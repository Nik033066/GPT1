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
4. Per trovare il campo di ricerca: usa selettori generici come "input[type='search']", "input[name='q']", "textarea", o cerca nel testo estratto
5. Pagina risultati → click sul primo risultato (h3)
6. Obiettivo completato → done con risposta
7. Selettori specifici: Su Google usa #APjFqb, su Bing usa #sb_form_q o input[name='q']
8. Se il selettore non funziona, prova input[name='q'] o input[type='search']

LINGUAGGIO:
- Tutti i testi (thought, text, query digitata) devono essere frasi chiare in italiano naturale.
- Per type usa frasi descrittive (es. "Cerco informazioni su Poste Italiane"), non keyword secche.
- Per done/extract scrivi una risposta leggibile in italiano, senza JSON, riassumendo cosa hai trovato.

JSON:"""


def _is_url(s: str) -> bool:
    return s.startswith("http") or "." in s

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

    def _has_search_box(self, text: str) -> bool:
        t = text or ""
        return (
            "#APjFqb" in t
            or "#sb_form_q" in t
            or "[TEXTAREA]" in t
            or "TEXTAREA" in t
            or "[INPUT" in t
            or "input[type='search']" in t
            or "input[name='q']" in t
        )

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
        consent_keywords = [
            "prima di continuare", "before continuing", 
            "accetta tutto", "accept all", 
            "gestisci opzioni", "manage options",
            "informativa privacy", "privacy policy",
            "cookie policy", "i agree", "acconsento"
        ]
        
        if any(k in t for k in consent_keywords):
            if "#l2aglb" in t:
                return "#L2AGLb"
            
            patterns = [
                r'\[BUTTON\] ".*Accetta.*" => (\S+)',
                r'\[BUTTON\] ".*Accept.*" => (\S+)',
                r'\[BUTTON\] ".*Agree.*" => (\S+)',
                r'\[BUTTON\] ".*Consent.*" => (\S+)',
                r'\[BUTTON\] ".*OK.*" => (\S+)'
            ]
            
            for pat in patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    return m.group(1)
            
            if "bnp_btn_accept" in t:
                return "#bnp_btn_accept"
                
            return None
        return None

    def _find_search_selector(self, text: str, url: str = "") -> str | None:
        """Trova il selettore appropriato per il campo di ricerca in base al sito"""
        url_lower = url.lower()
        text_lower = text.lower()
        
        if "google.com" in url_lower:
            return "#APjFqb"
        
        if "bing.com" in url_lower:
            bing_selectors = ["#sb_form_q", "input[name='q']", "[data-testid='search-input']"]
            for sel in bing_selectors:
                if sel in text_lower:
                    return sel
            return "#sb_form_q"
        
        if "duckduckgo.com" in url_lower:
            return "#search_form_input"
        
        generic_selectors = ["input[name='q']", "input[type='search']", "textarea[name='q']"]
        for sel in generic_selectors:
            if sel in text_lower:
                return sel
        
        return "input[name='q']"

    def next(self, goal: str, obs: Obs, mem: str) -> Act:
        is_empty = self._is_empty_page(obs.url)
        url_lower = (obs.url or "").lower()
        is_blocked = self._is_critical_block(obs.url, obs.text)
        
        if "bing.com" in url_lower and "/search" not in url_lower and obs.step > 0:
            if "type" in mem.lower() and "#apjfqb" in mem.lower():
                search_sel = self._find_search_selector(obs.text, obs.url)
                if search_sel:
                    search_text = goal
                    clean_text = search_text.lower()
                    for word in ["cercami", "trovami", "pagina", "sito", "web"]:
                        clean_text = clean_text.replace(word, "")
                    search_text = clean_text.strip() or search_text
                    
                    return Act(action="type", selector=search_sel, text=search_text, key="Enter", thought="Correzione: uso selettore appropriato per Bing")
        
        if is_empty and obs.step == 0:
            if _is_url(goal):
                return Act(action="navigate", url=goal, thought=f"Navigo all'URL iniziale: {goal}")

        cookie_sel = self._has_cookie_banner(obs.text)
        if cookie_sel and "click" not in mem.lower()[:50]:
            return Act(action="click", selector=cookie_sel, thought="Chiudo banner cookie")

        if "google." in url_lower and "/search" in url_lower and "type" in mem.lower() and "h3" not in obs.text:
            return Act(action="scroll", dy=700, thought="Scorro per vedere risultati di ricerca")
        
        if "google." in url_lower and "/search" not in url_lower and "type" in mem.lower():
            if "press:Enter" not in mem.lower():
                return Act(action="press", key="Enter", thought="Invio la ricerca su Google")
            else:
                return Act(action="wait", ms=1000, thought="Attendo risultati ricerca")

        if is_blocked and "google." in url_lower:
            return Act(
                action="done",
                text="Google ha mostrato una verifica (captcha/robot). Non posso completarla in automatico. Apri la pagina e completa la verifica, poi rilancia la richiesta.",
                thought="Blocco captcha su Google",
            )

        if not is_empty and self._too_many_extracts(mem):
            return Act(action="navigate", url=consts.DEFAULT_HOME_URL, thought="Cambio pagina per continuare la ricerca")

        if (
            (not is_blocked)
            and (not is_empty)
            and (obs.step < 3)
            and ("scroll" not in mem.lower())
            and self._few_interactives(obs.text)
        ):
            if ("/search" not in url_lower) and ("?q=" not in url_lower) and (not self._has_search_box(obs.text)):
                return Act(action="scroll", dy=700, thought="Scorro per trovare pulsanti o link")
        
        hints = []
        if is_blocked:
            hints.append("⚠️ BLOCCO/CAPTCHA: cambia strategia (es. altro sito o altra fonte).")
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
