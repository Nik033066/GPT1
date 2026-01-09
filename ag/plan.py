from __future__ import annotations

from dataclasses import dataclass
import re

from ag.js import load_obj
from ag.llm import LLM
from ag.sch import Act, Obs
from ag import consts
from ag.logger import get_logger

logger = get_logger(__name__)


SYS = """Sei un Agente AI che naviga il web.

AZIONI (JSON):
{"thought": "...", "action": "navigate|click|type|press|scroll|wait|back|done", "url": "...", "selector": "...", "text": "...", "key": "Enter"}

REGOLE:
1. Pagina vuota (about:blank) → DEVI usare navigate
2. Banner cookie ("Prima di continuare", "Accetta tutto") → click su #L2AGLb o il bottone Accetta
3. Campo ricerca visibile → type con la query, poi press Enter
4. Pagina risultati → click sul primo risultato (h3)
5. Obiettivo completato → done con risposta

LINGUAGGIO:
- Tutti i testi (thought, text, query digitata) devono essere frasi chiare in italiano naturale.
- Per type usa frasi descrittive (es. "Cerco informazioni su Poste Italiane"), non keyword secche.
- Per done/extract scrivi una risposta leggibile in italiano, senza JSON, riassumendo cosa hai trovato.

JSON:"""


@dataclass
class Planner:
    llm: LLM
    mode: str = "hybrid"
    demo_mode: bool = False

    def _too_many_extracts(self, mem: str) -> bool:
        return mem.lower().count("extract") >= 3

    def _is_critical_block(self, url: str, text: str) -> bool:
        u = (url or "").lower()
        t = (text or "").lower()
        critical = ["captcha", "robot", "verify you are human", "unusual traffic"]
        return any(p in u or p in t for p in critical)
    
    def _is_empty_page(self, url: str) -> bool:
        return not url or url == "about:blank"

    def _few_interactives(self, text: str) -> bool:
        if not text:
            return True
        lines = text.splitlines()
        count = 0
        for ln in lines:
            if ("[BUTTON]" in ln) or ("[A]" in ln) or ("[INPUT" in ln) or ("TEXTAREA" in ln):
                count += 1
            if count >= 3:
                return False
        return True
    
    def _has_cookie_banner(self, text: str) -> str | None:
        t = (text or "").lower()
        if "prima di continuare" in t or "before continuing" in t:
            if "#l2aglb" in t.lower():
                return "#L2AGLb"
            if '"accetta tutto"' in t.lower():
                m = re.search(r'"Accetta tutto"[^\n]*=>\s*(\S+)', text, re.I)
                if m:
                    return m.group(1)
            return "#L2AGLb"  # Default Google
        return None

    def next(self, goal: str, obs: Obs, mem: str) -> Act:
        is_empty = self._is_empty_page(obs.url)
        
        cookie_sel = self._has_cookie_banner(obs.text)
        if cookie_sel and "click" not in mem.lower()[:50]:
            return Act(action="click", selector=cookie_sel, thought="Chiudo banner cookie")
        
        if self._is_critical_block(obs.url, obs.text):
            return Act(action="navigate", url=consts.ALT_SEARCH_URL, thought="Blocco, provo motore alternativo")

        if not is_empty and self._too_many_extracts(mem):
            return Act(action="navigate", url=consts.DEFAULT_HOME_URL, thought="Cambio pagina per continuare la ricerca")

        if not is_empty and "scroll" not in mem.lower() and self._few_interactives(obs.text):
            return Act(action="scroll", dy=700, thought="Scorro per trovare pulsanti o link")
        
        hints = []
        if "Loop" in mem or "WARNING" in mem:
            hints.append("⚠️ LOOP! CAMBIA STRATEGIA!")
        if is_empty:
            hints.append("⚠️ PAGINA VUOTA! Usa navigate!")

        user_prompt = f"""OBIETTIVO: {goal}

URL: {obs.url or "about:blank"}
Step: {obs.step}

PAGINA:
{obs.text[:2000] if obs.text else "(VUOTA)"}

FATTO: {mem or "-"}

{chr(10).join(hints)}

JSON:"""

        for attempt in range(3):
            try:
                raw = self.llm.gen(SYS, user_prompt)
                obj = load_obj(raw)
                act = Act.model_validate(obj)
                
                # Fix: pagina vuota + extract/done = errore
                if is_empty and act.action in ("extract", "done") and obs.step < 2:
                    if attempt < 2:
                        user_prompt += "\n❌ ERRORE! Pagina vuota = devi navigare!"
                        continue
                    return Act(action="navigate", url=consts.DEFAULT_HOME_URL, thought="Fallback")
                
                if act.action == "navigate" and not act.url:
                    continue
                
                return act
            except Exception as e:
                logger.warning("planner attempt %s failed: %s", attempt + 1, e)
                continue
        
        if is_empty:
            return Act(action="navigate", url=consts.DEFAULT_HOME_URL, thought="Fallback")
        return Act(action="done", text="Errore.", thought="Fallback")
