from __future__ import annotations

from dataclasses import dataclass
import subprocess
import sys
import webbrowser
from typing import Any, Optional

from ag import consts
from ag.logger import get_logger
from ag import sys_input

logger = get_logger(__name__)


@dataclass
class Br:
    timeout_ms: int = consts.DEFAULT_TIMEOUT_MS
    browser: str = "playwright"
    cdp_url: str = ""
    browser_app: str = ""
    auto_consent: bool = False
    headless: bool = False
    os_cursor: bool = False
    action_delay_ms: int = 0
    view_only: bool = False
    _attached: bool = False
    _pw: Any = None
    _browser: Any = None
    _ctx: Any = None
    page: Any = None

    def _default_cdp_url(self) -> str:
        return consts.DEFAULT_CDP_URL

    async def start(self) -> None:
        try:
            from playwright.async_api import async_playwright
        except Exception as e:
            logger.error("Playwright non trovato")
            raise RuntimeError("playwright_missing") from e

        self._pw = await async_playwright().start()
        
        # Always use managed Playwright mode (Chromium)
        try:
            self._browser = await self._pw.chromium.launch(headless=self.headless)
        except Exception as e:
             logger.error(f"Errore avvio Chromium: {e}")
             raise RuntimeError("playwright_browsers_missing") from e
        self._attached = False

        contexts = list(getattr(self._browser, "contexts", []))
        self._ctx = contexts[0] if contexts else await self._browser.new_context()
        self.page = await self._ctx.new_page()
        self.page.set_default_timeout(self.timeout_ms)

        # Add stealth scripts
        await self.page.add_init_script(consts.JS_HIDE_WEBDRIVER)
        await self.install_cursor()

    async def stop(self) -> None:
        if self.view_only:
            if self._pw is not None:
                await self._pw.stop()
            return

        if self._attached:
            if self.page is not None:
                try:
                    await self.page.close()
                except Exception:
                    pass
            if self._pw is not None:
                await self._pw.stop()
            return

        if self._ctx is not None:
            await self._ctx.close()
        if self._browser is not None:
            await self._browser.close()
        if self._pw is not None:
            await self._pw.stop()

    async def goto(self, url: str) -> None:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        if self.view_only:
            if sys.platform == "darwin":
                subprocess.run(["open", url], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                webbrowser.open(url)
            return

        await self.page.goto(url, wait_until="domcontentloaded")
        if self.auto_consent and "google." in url:
            if await self._click_consent():
                await self.page.wait_for_timeout(400)

    async def back(self) -> None:
        if self.view_only:
            return
        await self.page.go_back(wait_until="domcontentloaded")

    async def title(self) -> str:
        if self.view_only:
            return "Browser esterno"
        try:
            t = await self.page.title()
            return str(t)
        except Exception:
            return ""

    async def url(self) -> str:
        if self.view_only:
            return ""
        try:
            return str(self.page.url)
        except Exception:
            return ""

    async def install_cursor(self) -> None:
        if self.view_only or not self.page:
            return
        try:
            await self.page.evaluate(consts.JS_INSTALL_CURSOR)
        except Exception as e:
            logger.debug(f"Errore installazione cursore: {e}")

    async def set_status(self, msg: str) -> None:
        if self.view_only or not self.page:
            return
        try:
            safe_msg = msg.replace("'", "\\'")
            await self.page.evaluate(f"const el = document.getElementById('ag-status'); if(el) el.innerText = '🤖 {safe_msg}';")
        except Exception:
            pass

    async def move_cursor_visual(self, x: float, y: float) -> None:
        if self.view_only or not self.page:
            return
        try:
            await self.page.evaluate(f"const el = document.getElementById('ag-cursor'); if(el) el.style.transform = 'translate({x}px, {y}px)'")
        except Exception:
            pass

    async def get_screen_offset(self) -> tuple[float, float]:
        if self.view_only or not self.page:
            return (0.0, 0.0)
        try:
            res = await self.page.evaluate(consts.JS_GET_SCREEN_OFFSET)
            return (float(res[0]), float(res[1]))
        except Exception:
            return (0.0, 0.0)

    async def _get_physical_coords(self, x: float, y: float, offset: tuple[float, float] | None = None) -> tuple[float, float]:
        if offset is None:
            off_x, off_y = await self.get_screen_offset()
        else:
            off_x, off_y = offset
        return off_x + x, off_y + y

    async def mouse_move_physical(self, x: float, y: float, offset: tuple[float, float] | None = None) -> None:
        # Visual cursor update
        await self.move_cursor_visual(x, y)
        if self.os_cursor and not self.headless:
            try:
                px, py = await self._get_physical_coords(x, y, offset=offset)
                sys_input.move(px, py)
            except Exception:
                pass
        
        try:
            await self.page.mouse.move(x, y)
        except Exception:
            pass

    async def click_physical(self, x: float, y: float) -> None:
        # Move visual cursor to location
        await self.move_cursor_visual(x, y)
        
        try:
            await self.page.mouse.click(x, y)
        except Exception:
            pass

    async def screenshot(self, path: str) -> None:
        if self.view_only or not self.page:
            return
        for _ in range(2):
            try:
                await self.page.screenshot(path=path)
                return
            except Exception as e:
                msg = str(e)
                if "Execution context was destroyed" in msg or "most likely because of a navigation" in msg:
                    try:
                        await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
                        await self.page.wait_for_timeout(100)
                    except Exception:
                        return
                    continue
                logger.error(f"Screenshot failed: {e}")
                return

    async def extract_text(self, budget: int) -> str:
        if self.view_only:
            return "Browser aperto in modalità esterna. Il contenuto non è accessibile."
        if not self.page:
            return ""

        last_err: Exception | None = None
        for _ in range(3):
            try:
                t = await self.page.evaluate(consts.JS_EXTRACT_TEXT)
                if not isinstance(t, str):
                    return ""
                t = " ".join(t.split())
                return t[:budget]
            except Exception as e:
                last_err = e
                msg = str(e)
                if "Execution context was destroyed" in msg or "most likely because of a navigation" in msg:
                    try:
                        await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
                        await self.page.wait_for_timeout(150)
                    except Exception:
                        break
                    continue
                break

        if last_err is not None:
            logger.debug(f"extract_text failed: {last_err}")
        return ""

    async def bbox_center(self, selector: str) -> Optional[tuple[float, float, float]]:
        if self.view_only:
            return None
        loc = self.page.locator(selector).first
        try:
            box = await loc.bounding_box()
            if not box:
                return None
            cx = box["x"] + (box["width"] / 2.0)
            cy = box["y"] + (box["height"] / 2.0)
            w = min(box["width"], box["height"])
            return cx, cy, w
        except Exception:
            return None

    async def click_at(self, x: float, y: float) -> None:
        if self.view_only:
            return
        await self.click_physical(x, y)

    async def _click_consent(self) -> bool:
        if self.view_only:
            return False
        from playwright.async_api import TimeoutError as PwTimeout

        frames = list(getattr(self.page, "frames", []))
        
        # Check main page first
        for sel in consts.COOKIE_CONSENT_SELECTORS:
            try:
                loc = self.page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    await loc.click()
                    return True
            except Exception:
                continue

        # Check frames
        for fr in frames:
            for sel in consts.COOKIE_CONSENT_SELECTORS:
                try:
                    loc = fr.locator(sel).first
                    await loc.wait_for(state="visible", timeout=500)
                    await loc.click()
                    return True
                except PwTimeout:
                    continue
                except Exception:
                    continue
        return False

    async def type_into(self, selector: str, text: str) -> None:
        if self.view_only:
            return
        
        parts = [selector]
        if "," in selector:
            parts = [p.strip() for p in selector.split(",") if p.strip()]

        cands: list[str] = []
        for p in parts:
            if ":visible" not in p:
                cands.append(f"{p}:visible")
            cands.append(p)
        
        target = None
        for c in cands:
            try:
                loc = self.page.locator(c).first
                if await loc.count() > 0 and await loc.is_visible():
                    target = loc
                    break
            except Exception:
                continue
        
        if not target:
            # Fallback generico
            try:
                target = self.page.locator("input[type='text'], textarea, [contenteditable]").first
            except Exception:
                pass
        
        if target:
            try:
                # Move visual cursor to center of element
                box = await target.bounding_box()
                if box:
                    cx = box["x"] + box["width"] / 2
                    cy = box["y"] + box["height"] / 2
                    await self.move_cursor_visual(cx, cy)

                await target.click()
                await self.page.wait_for_timeout(200)
                await target.fill("")
                await target.type(text, delay=50)
            except Exception:
                pass
    
    async def press(self, key: str) -> None:
        if self.view_only or not self.page:
            return
        try:
            await self.page.keyboard.press(key)
        except Exception:
            pass

    async def scroll(self, dy: int) -> None:
        if self.view_only or not self.page:
            return
        try:
            await self.page.mouse.wheel(0, int(dy))
        except Exception:
            try:
                await self.page.evaluate("(dy) => window.scrollBy(0, dy)", int(dy))
            except Exception:
                pass
