from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import quote_plus

from ag.js import load_obj
from ag.llm import LLM
from ag.sch import Act, Obs
from ag.nlp import GoalClassifier


SYS = (
    "Sei un Agente AI avanzato capace di navigare il web e usare applicazioni complesse.\n"
    "Il tuo obiettivo è completare il task dell'utente usando il browser.\n"
    "NON rispondere 'ok' o 'fatto' senza aver prima eseguito le azioni necessarie nel browser.\n"
    "Produci SEMPRE un oggetto JSON valido.\n\n"
    "SCHEMA JSON:\n"
    "{\n"
    '  "thought": "Ragionamento su cosa fare (es. \'Pagina non caricata, attendo\').",\n'
    '  "action": "navigate" | "click" | "type" | "press" | "scroll" | "wait" | "extract" | "back" | "done",\n'
    '  "url": "URL..." (solo per navigate),\n'
    '  "selector": "CSS selector" (per click, type, extract),\n'
    '  "text": "..." (per type, done),\n'
    '  "key": "Enter" | "Tab" | ... (per press),\n'
    '  "dy": 700 (per scroll, positivo giù / negativo su),\n'
    '  "ms": 1000 (per wait)\n'
    "}\n\n"
    "REGOLE E STRATEGIE:\n"
    "1. RICERCA: Se devi cercare e NON sei su Google, naviga su google.com. Se sei già su Google (url contiene 'google'), NON ricaricare la pagina: usa 'type' nella barra di ricerca e poi 'press' Enter.\n"
    "2. APPLICAZIONI: Usa la sezione 'ELEMENTI INTERATTIVI' per trovare i selettori corretti. Se un elemento non c'è, aspetta o scorri.\n"
    "3. NAVIGAZIONE: Se un click apre una nuova tab, il sistema la gestirà. Se serve tornare indietro, usa 'back'.\n"
    "4. DATI: Se devi estrarre info, usa 'extract' (copia tutto il testo visibile) e poi analizzalo nella memoria.\n"
    "5. ERRORE: Se un'azione fallisce (vedi MEMORIA), prova un approccio diverso (es. altro selettore o wait).\n"
    "6. COMPLETAMENTO: Quando hai finito, usa action: done con la risposta finale in 'text'.\n\n"
    "ESEMPI:\n"
    '{"thought": "Apro Google per cercare info", "action": "navigate", "url": "https://www.google.com"}\n'
    '{"thought": "Scrivo la query", "action": "type", "selector": "[name=\'q\']", "text": "meteo Roma"}\n'
    '{"thought": "Premo invio", "action": "press", "key": "Enter"}\n'
    '{"thought": "Scorro per vedere altri risultati", "action": "scroll", "dy": 800}\n'
    '{"thought": "Clicco sul primo risultato", "action": "click", "selector": "h3"}\n'
)

DEMO_SYS_EXTRA = (
    "\nDEMO MODE (UX):\n"
    "- Preferisci passaggi piccoli e visibili.\n"
    "- Se sei su Google e devi trovare un sito, non saltare direttamente al sito: usa 'type' nella barra, poi 'press' Enter, poi 'click' sul risultato.\n"
    "- Evita di costruire URL di ricerca direttamente; usa interazioni (type/press/click).\n"
)


@dataclass
class Planner:
    llm: LLM
    mode: str = "hybrid"
    demo_mode: bool = False
    classifier: GoalClassifier = GoalClassifier()

    def _is_google_sorry(self, url: str) -> bool:
        u = (url or "").lower()
        return "google.com/sorry" in u or "/sorry/" in u

    def _is_ddg_bot_challenge(self, url: str, text: str) -> bool:
        u = (url or "").lower()
        if "duckduckgo.com" not in u:
            return False
        t = (text or "").lower()
        return "bots use duckduckgo" in t or "complete the following challenge" in t or "unfortunately" in t

    def _extract_search_query(self, goal: str) -> str:
        m = re.search(r"\bcerca\b\s+(.+)$", goal, flags=re.IGNORECASE)
        if m:
            q = m.group(1)
        else:
            q = self.classifier.extract_query(goal)
        q = re.sub(r"https?://\S+|www\.\S+", " ", q, flags=re.IGNORECASE)
        q = re.sub(r"\b(apri|vai|naviga|visita|portami|open|go|navigate)\b", " ", q, flags=re.IGNORECASE)
        q = re.sub(r"\bgoogle\.com\b|\bgoogle\b", " ", q, flags=re.IGNORECASE)
        q = re.sub(r"\s+", " ", q).strip(" \t\n\r.,:;\"'")
        return q or goal.strip()

    def _news_rss_url(self, query: str) -> str:
        q = quote_plus(query)
        return f"https://news.google.com/rss/search?q={q}&hl=it&gl=IT&ceid=IT:it"

    def _goal_is_search(self, goal: str) -> bool:
        return re.search(r"\b(cerca|trova|search|find)\b", goal, flags=re.IGNORECASE) is not None

    def next(self, goal: str, obs: Obs, mem: str) -> Act:
        if self.mode == "hybrid" and (self._is_google_sorry(obs.url) or self._is_ddg_bot_challenge(obs.url, obs.text)):
            q = self._extract_search_query(goal)
            return Act(
                action="navigate",
                url=self._news_rss_url(q),
                thought="Risultati bloccati da CAPTCHA/anti-bot, uso RSS di Google News.",
            )

        if (
            self.mode == "hybrid"
            and not self.demo_mode
            and "google.com" in (obs.url or "").lower()
            and "/search?" not in (obs.url or "").lower()
            and self._goal_is_search(goal)
        ):
            q = self._extract_search_query(goal)
            return Act(
                action="navigate",
                url=f"https://www.google.com/search?q={quote_plus(q)}",
                thought="Eseguo la ricerca costruendo direttamente l'URL.",
            )

        if self.mode == "hybrid" and "/search?" in (obs.url or "").lower() and "type textarea[name='q']=" in mem:
            return Act(action="done", text="Query inviata.")

        if self.mode == "hybrid" and obs.step == 0 and obs.url in {"", "about:blank"} and "google.com" not in obs.url:
            # Analisi matematica dell'intento
            intent = self.classifier.classify(goal)
            
            if intent == "navigate":
                url = self.classifier.extract_url(goal)
                if url:
                    return Act(action="navigate", url=url, thought="URL rilevato nel comando, navigo direttamente.")
                
                # Gestione siti comuni noti (logica espandibile)
                g_lower = goal.lower()
                if "youtube" in g_lower:
                    return Act(action="navigate", url="https://www.youtube.com", thought="Navigo su YouTube.")
                
            # Se è ricerca o navigazione generica senza URL, passa da Google
            if intent in ("search", "navigate"):
                return Act(action="navigate", url="https://www.google.com", thought="Inizio la sessione navigando su Google.")

        user = (
            f"OBIETTIVO:\n{goal}\n\n"
            f"STATO:\nurl={obs.url}\ntitle={obs.title}\nstep={obs.step}\n\n"
            f"TESTO_PAGINA (estratto):\n{obs.text}\n\n"
            f"MEMORIA:\n{mem}\n\n"
            "Prossima azione JSON:"
        )
        sys_prompt = SYS + (DEMO_SYS_EXTRA if self.demo_mode else "")
        last_err = ""
        for k in range(3):
            raw = self.llm.gen(sys_prompt, user if k == 0 else f"{user}\n\nErrore: {last_err}\nRiprova SOLO JSON:")
            try:
                obj = load_obj(raw)
                return Act.model_validate(obj)
            except Exception as e:
                last_err = str(e)
        return Act(action="extract")
