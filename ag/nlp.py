from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class GoalClassifier:
    """
    Classificatore leggero per intent detection.
    Usa pattern generici invece di liste hardcoded.
    """
    
    def classify(self, text: str) -> str:
        """
        Classifica l'intento del goal.
        Returns: "navigate", "search", o "generic"
        """
        t = text.lower()
        
        # Pattern per navigazione (verbi + contesto)
        nav_pattern = r"\b(apri|vai|naviga|visita|portami|open|go\s+to|navigate|visit)\b"
        if re.search(nav_pattern, t):
            return "navigate"
        
        # Pattern per ricerca
        search_pattern = r"\b(cerca|trova|search|find|what|come|dove|quando|chi|perché)\b"
        if re.search(search_pattern, t):
            return "search"
        
        # Se contiene un URL/dominio, è navigazione
        if re.search(r"https?://|www\.|\.com|\.it|\.org|\.net", t):
            return "navigate"
        
        return "generic"

    def extract_url(self, text: str) -> str | None:
        """Estrae URL dal testo se presente."""
        match = re.search(r'(https?://[^\s]+|www\.[^\s]+)', text, re.IGNORECASE)
        if match:
            url = match.group(1)
            if not url.startswith("http"):
                url = "https://" + url
            return url
        return None

    def extract_query(self, text: str) -> str:
        """Estrae la query di ricerca pulendo il testo."""
        # Rimuove verbi comuni
        clean = re.sub(
            r"\b(cerca|trova|apri|vai|naviga|visita|dimmi|dammi|search|find|open|go)\b",
            "", text, flags=re.IGNORECASE
        )
        # Rimuove preposizioni iniziali
        clean = re.sub(r"^\s*(il|lo|la|i|gli|le|un|una|di|a|da|in|su|per|the|a|an)\s+", "", clean, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", clean).strip()
