from __future__ import annotations

import math
import re
from dataclasses import dataclass

@dataclass
class IntentScore:
    search: float
    navigate: float
    chat: float

class GoalClassifier:
    """
    Classificatore di intenti basato su punteggi pesati e funzioni di attivazione sigmoide.
    Sostituisce le euristiche fragili con un modello matematico deterministico ma flessibile.
    """
    
    # Pesi per i verbi/parole chiave
    SEARCH_TERMS = {
        "cerca": 2.0, "trova": 2.0, "dammi": 1.0, "chi": 1.5, "cosa": 1.5, "quando": 1.5,
        "dove": 1.5, "come": 1.0, "meteo": 2.0, "prezzo": 2.0, "costo": 2.0, "orario": 2.0,
        "search": 2.0, "find": 2.0, "google": 1.5
    }
    
    NAV_TERMS = {
        "vai": 2.0, "apri": 2.0, "naviga": 2.0, "visita": 2.0, "portami": 2.0,
        "open": 2.0, "go": 2.0, "navigate": 2.0, "url": 3.0, "sito": 1.5, "pagina": 1.5,
        "http": 5.0, "www": 5.0, ".com": 3.0, ".it": 3.0
    }
    
    def __init__(self) -> None:
        self._search_re = self._compile_terms(self.SEARCH_TERMS)
        self._nav_re = self._compile_terms(self.NAV_TERMS)

    def _compile_terms(self, terms: dict[str, float]) -> re.Pattern:
        # Crea una regex ottimizzata per trovare tutti i termini
        sorted_terms = sorted(terms.keys(), key=len, reverse=True)
        pattern = "|".join(map(re.escape, sorted_terms))
        return re.compile(f"\\b({pattern})\\b", re.IGNORECASE)

    def _sigmoid(self, x: float, k: float = 1.0, x0: float = 0.0) -> float:
        """Funzione logistica: 1 / (1 + e^(-k(x-x0)))"""
        return 1.0 / (1.0 + math.exp(-k * (x - x0)))

    def classify(self, text: str) -> str:
        """
        Calcola i punteggi per ogni categoria e restituisce l'intento dominante.
        """
        scores = self._compute_scores(text)
        
        # Logica di decisione basata sui punteggi
        if scores.navigate > 0.6 and scores.navigate > scores.search:
            return "navigate"
        if scores.search > 0.4:
            return "search"
        
        # Fallback su euristica di lunghezza se i punteggi sono bassi
        # (se è corto e non ha verbi, è probabilmente una query di ricerca)
        words = len(text.split())
        if words < 8 and scores.chat < 0.3:
            return "search"
            
        return "generic"

    def extract_url(self, text: str) -> str | None:
        """Estrae URL usando pattern matching robusto."""
        # Regex complessa per URL validi
        url_pattern = re.compile(
            r'(?:(?:https?://)|(?:www\.))'  # Protocollo o www
            r'(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'  # Dominio
            r'(?:/[^\s]*)?'  # Path opzionale
        )
        match = url_pattern.search(text)
        if match:
            url = match.group(0)
            if not url.startswith("http"):
                url = "https://" + url
            return url
        return None

    def extract_query(self, text: str) -> str:
        """Pulisce il testo per ottenere la query di ricerca."""
        # Rimuove verbi di comando comuni
        clean = text
        for term in ["cerca", "trova", "dammi", "dimmi", "search", "find"]:
             clean = re.sub(f"\\b{term}\\b", "", clean, flags=re.IGNORECASE)
        
        # Rimuove articoli e preposizioni comuni se all'inizio
        clean = re.sub(r"^\s*(il|lo|la|i|gli|le|un|uno|una|di|a|da|in|su|per)\s+", "", clean, flags=re.IGNORECASE)
        return clean.strip()

    def _compute_scores(self, text: str) -> IntentScore:
        search_score = 0.0
        nav_score = 0.0
        
        # Analisi Search
        for match in self._search_re.finditer(text):
            term = match.group(1).lower()
            search_score += self.SEARCH_TERMS.get(term, 0.0)
            
        # Analisi Nav
        for match in self._nav_re.finditer(text):
            term = match.group(1).lower()
            nav_score += self.NAV_TERMS.get(term, 0.0)
            
        # Analisi URL espliciti
        if "http" in text or "www." in text:
            nav_score += 5.0
            
        # Normalizzazione con Sigmoide
        # k=1.0, x0=2.0 significa che un punteggio grezzo di 2.0 dà 0.5 probabilità
        s_norm = self._sigmoid(search_score, k=1.2, x0=2.0)
        n_norm = self._sigmoid(nav_score, k=1.2, x0=2.0)
        
        return IntentScore(search=s_norm, navigate=n_norm, chat=0.0)
