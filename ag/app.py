from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    file_root = Path(__file__).parent.parent
    sys.path.append(str(file_root))

from typing import Optional

from ag.cfg import Cfg
from ag.cur import Cur
from ag.llm import HfLLM, MockLLM, LLM
from ag.mem import Mem
from ag.plan import Planner
from ag.sch import Act, Obs, RunRes, Step
from ag.br import Br
from ag.logger import get_logger

logger = get_logger(__name__)


class AgentSession:
    def __init__(self, llm: LLM, cfg: Cfg):
        self._planner = Planner(llm=llm, mode=cfg.planner_mode, demo_mode=cfg.demo_mode)
        self._mem = Mem()
        self._cur = Cur(demo_mode=cfg.demo_mode)

    async def run(self, goal: str, cfg: Cfg, br: Br) -> RunRes:
        res = RunRes(goal=goal)
        obs = Obs(url=await br.url(), title=await br.title(), text="", step=0)

        for step_i in range(cfg.max_steps):
            obs.step = step_i
            obs.url = await br.url()
            obs.title = await br.title()
            obs.text = await br.extract_text(cfg.text_budget)

            await br.screenshot("latest.png")

            if br.view_only and step_i > 0:
                if not res.answer:
                    res.answer = "Non ho eseguito nessuna navigazione."
                break

            if len(res.steps) >= 3:
                last_3 = [s.act for s in res.steps[-3:]]
                if all(a.action == last_3[0].action and a.selector == last_3[0].selector for a in last_3):
                    self._mem.add("SYSTEM WARNING: Loop rilevato. CAMBIA STRATEGIA.")
                    print("⚠️ Loop rilevato")

            print(f"📍 step={step_i} url={obs.url} title={obs.title}")
            print("🧠 Pianifico...")
            
            t0 = time.perf_counter()
            plan_obs = obs.model_copy()
            plan_obs.text = plan_obs.text[: cfg.model_text_budget]
            
            try:
                act = await asyncio.wait_for(
                    asyncio.to_thread(self._planner.next, goal, plan_obs, self._mem.view()),
                    timeout=cfg.plan_timeout_ms / 1000.0,
                )
            except asyncio.TimeoutError:
                msg = f"Timeout dopo {cfg.plan_timeout_ms}ms"
                res.answer = msg
                res.steps.append(Step(act=Act(action="done", text=msg), obs=obs.model_copy()))
                break
            
            dt = time.perf_counter() - t0
            print(f"⏱️ {dt:.1f}s")

            if act.thought:
                print(f"🧠 {act.thought}")

            act_str = str(act.action)
            if act.selector:
                act_str += f" '{act.selector}'"
            if act.text:
                act_str += f" text='{act.text}'"
            if act.url:
                act_str += f" → '{act.url}'"
            print(f"⚡ {act_str}")

            should_stop = await _handle_action(act, obs, self._mem, br, self._cur, res)
            if should_stop:
                break

        if not res.answer:
            res.answer = (await br.extract_text(2200)) or "fine"
        return res


async def _move_cursor_to(br: Br, cur: Cur, selector: str) -> bool:
    await br.set_status("Muovo cursore...")
    bb = await br.bbox_center(selector)
    if bb is None:
        return False
    
    cx, cy, w = bb
    
    
    if cur.x == 0.0 and cur.y == 0.0:
        
        cur.set(cx, cy)
    
    if not br.headless:
        for x, y, delay_ms in cur.iter_timed(cx, cy, w):
            await br.move_cursor(x, y)
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)
    else:
        # Anche in headless mode, aggiungi delay in demo mode per rendere visibile il movimento
        if cur.demo_mode:
            for x, y, delay_ms in cur.iter_timed(cx, cy, w):
                await br.move_cursor(x, y)
                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000.0)
        else:
            for x, y in cur.move(cx, cy, w):
                await br.move_cursor(x, y)
    
    await br.move_cursor(cx, cy)
    return True


async def _handle_action(act: Act, obs: Obs, mem: Mem, br: Br, cur: Cur, res: RunRes) -> bool:
    if act.action == "done":
        res.answer = act.text if act.text else obs.text[:1200]
        res.steps.append(Step(act=act, obs=obs.model_copy()))
        return True

    if act.action == "navigate" and act.url:
        await br.set_status(f"Navigo su {act.url}...")
        await br.goto(act.url)
        mem.add(f"goto {act.url}")
        if br.view_only:
            res.answer = f"Ho aperto {act.url}"
            res.steps.append(Step(act=act, obs=obs.model_copy()))
            return True
        if "/search?q=" in act.url:
            mem.add("qnav")
            
    elif act.action == "back":
        await br.set_status("Indietro...")
        await br.back()
        mem.add("back")
        
    elif act.action == "wait":
        ms = act.ms or 500
        await br.set_status(f"Attendo {ms}ms...")
        await asyncio.sleep(ms / 1000.0)
        mem.add(f"wait {ms}ms")
        
    elif act.action == "extract":
        await br.set_status("Leggo...")
        mem.add("extract")
        
    elif act.action == "type" and act.selector and act.text is not None:
        await br.set_status("Scrivo...")
        await _move_cursor_to(br, cur, act.selector)
        await br.type_into(act.selector, act.text)
        if act.key:
            await br.press(act.key)
        short = act.text.replace("\n", " ").strip()
        mem.add(f"type {act.selector}={short[:60]}")
        
    elif act.action == "press" and act.key:
        await br.set_status(f"Premo {act.key}...")
        await br.press(act.key)
        mem.add(f"press {act.key}")
    elif act.action == "press" and not act.key:
        mem.add("WARNING: press senza key")

    elif act.action == "scroll":
        dy = act.dy if act.dy is not None else 700
        await br.set_status("Scorro...")
        await br.scroll(dy)
        mem.add(f"scroll {dy}")
        
    elif act.action == "click" and act.selector:
        found = await _move_cursor_to(br, cur, act.selector)
        if not found:
            mem.add(f"miss {act.selector}")
        else:
            await br.set_status("Click!")
            bb2 = await br.bbox_center(act.selector)
            if bb2 is not None:
                cx2, cy2, _ = bb2
                await br.click_at(cx2, cy2)
                mem.add(f"click {act.selector}")
                
    else:
        mem.add(f"noop {act.action}")
        
    res.steps.append(Step(act=act, obs=obs.model_copy()))
    if not br.view_only and not br.headless and br.action_delay_ms > 0 and getattr(br, "page", None) is not None:
        try:
            await br.page.wait_for_timeout(br.action_delay_ms)
        except Exception:
            pass
    return False


async def _run_goal(goal: str, cfg: Cfg, llm: LLM, br: Br) -> RunRes:
    session = AgentSession(llm=llm, cfg=cfg)
    try:
        return await session.run(goal, cfg, br)
    except Exception as e:
        logger.error(f"Errore: {e}")
        return RunRes(goal=goal, answer=f"Errore: {e}")


async def async_main(args: argparse.Namespace) -> int:
    base = Cfg()
    cfg = Cfg(
        model_id=base.model_id,
        hf_device=base.hf_device,
        max_steps=base.max_steps,
        page_timeout_ms=base.page_timeout_ms,
        text_budget=base.text_budget,
        plan_timeout_ms=args.plan_timeout_ms or base.plan_timeout_ms,
        planner_mode=args.planner_mode or base.planner_mode,
        auto_consent=args.auto_consent if args.auto_consent is not None else base.auto_consent,
        headless=args.headless if args.headless is not None else base.headless,
        action_delay_ms=args.action_delay_ms if args.action_delay_ms is not None else base.action_delay_ms,
        demo_mode=args.demo_mode if args.demo_mode is not None else base.demo_mode,
        browser=args.browser or base.browser,
        cdp_url=args.cdp_url or base.cdp_url,
        browser_app=args.browser_app or base.browser_app,
    )

    try:
        llm = HfLLM(cfg.model_id, device=cfg.hf_device) if args.hf else MockLLM()
        llm.warmup()
    except Exception as e:
        if str(e) == "hf_auth_required":
            logger.error(f"ERRORE AUTORIZZAZIONE per {cfg.model_id}.")
            return 2
        raise

    br = Br(
        timeout_ms=cfg.page_timeout_ms,
        browser=cfg.browser,
        cdp_url=cfg.cdp_url,
        browser_app=cfg.browser_app,
        auto_consent=cfg.auto_consent,
        headless=cfg.headless,
        action_delay_ms=cfg.action_delay_ms,
    )
    
    try:
        try:
            await br.start()
        except RuntimeError as e:
            if "system_browser_not_found" in str(e) or "system_browser_connection_failed" in str(e):
                if cfg.browser == "system" or cfg.browser is None:
                    print("⚠️ Browser non trovato, uso Playwright...")
                    await br.stop()
                    br = Br(
                        timeout_ms=cfg.page_timeout_ms,
                        browser="playwright",
                        cdp_url="",
                        browser_app="",
                        auto_consent=cfg.auto_consent,
                        headless=cfg.headless,
                        action_delay_ms=cfg.action_delay_ms,
                    )
                    await br.start()
                else:
                    raise e
            else:
                raise e
        
        if args.goal:
            out = await _run_goal(args.goal, cfg, llm, br)
            print(out.model_dump_json(indent=2, exclude_none=True))
        else:
            print(f"🤖 Agente attivo ({cfg.model_id}). Scrivi cosa vuoi fare (o 'exit').")
            session = AgentSession(llm=llm, cfg=cfg)
            while True:
                try:
                    goal = input("\n👉 Tu: ").strip()
                except EOFError:
                    break
                
                if not goal:
                    continue
                if goal.lower() in ("exit", "quit", "esci"):
                    break
                
                print("⏳ Elaborazione...")
                out = await session.run(goal, cfg, br)
                print(f"🤖 Agente: {out.answer}")
                    
    except RuntimeError as e:
        if str(e) == "playwright_missing":
            logger.error("Playwright non installato.")
            return 3
        if str(e) == "playwright_browsers_missing":
            logger.error("Browser mancanti. Esegui: python3 -m playwright install chromium")
            return 4
        raise
    finally:
        await br.stop()
    
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="ag")
    p.add_argument("goal", type=str, nargs="?")
    p.add_argument("--hf", action="store_true")
    p.add_argument("--browser", choices=["playwright", "chromium", "system", "cdp"], default=None)
    p.add_argument("--cdp-url", type=str, default=None)
    p.add_argument("--browser-app", type=str, default=None)
    p.add_argument("--planner-mode", choices=["hybrid", "model"], default=None)
    p.add_argument("--auto-consent", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--headless", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--demo-mode", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--action-delay-ms", type=int, default=None)
    p.add_argument("--plan-timeout-ms", type=int, default=None)
    args = p.parse_args(argv)
    
    return asyncio.run(async_main(args))

if __name__ == "__main__":
    sys.exit(main())
