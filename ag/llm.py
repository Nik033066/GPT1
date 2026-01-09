from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Any, Protocol, cast

from ag.logger import get_logger
from ag import consts

logger = get_logger(__name__)


class LLM(Protocol):
    def gen(self, sys: str, user: str) -> str: ...
    def warmup(self) -> None: ...


@dataclass
class MockLLM:
    KNOWN_SITES: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.KNOWN_SITES is None:
            self.KNOWN_SITES = dict(consts.KNOWN_SITES)
    
    def gen(self, sys: str, user: str) -> str:
        u = user.lower()
        
        obj_match = re.search(r'OBIETTIVO:\s*(.+?)(?:\n|$)', user, re.I)
        goal = obj_match.group(1).strip().lower() if obj_match else ""
        
        if "about:blank" in u or ("url:" in u and "url: about:blank" in u.replace(" ", "")):
            url = self._find_direct_url(goal)
            if url:
                return f'{{"action":"navigate","url":"{url}","thought":"Navigo direttamente"}}'
            return f'{{"action":"navigate","url":"{consts.DEFAULT_HOME_URL}","thought":"Vado al motore predefinito"}}'
        
        if "prima di continuare" in u or "accetta tutto" in u:
            if "#L2AGLb" in user:
                return '{"action":"click","selector":"#L2AGLb","thought":"Accetto cookie"}'
            if "#W0wltc" in user:
                return '{"action":"click","selector":"#W0wltc","thought":"Rifiuto cookie"}'
        
        if "google.com" in u and not self._is_on_target(u, goal):
            url = self._find_direct_url(goal)
            if url:
                return f'{{"action":"navigate","url":"{url}","thought":"Navigo al sito richiesto"}}'
            
            if "#APjFqb" in user or "textarea" in u:
                query = self._smart_query(goal) if goal else "ricerca"
                return f'{{"action":"type","selector":"#APjFqb","text":"{query}","thought":"Scrivo la ricerca"}}'
        
        if "type #APjFqb" in u or "type textarea" in u:
            return '{"action":"press","key":"Enter","thought":"Invio la ricerca"}'
        
        if ("search?q=" in u or "risultati" in u) and "h3" in u:
            return '{"action":"click","selector":"h3","thought":"Clicco primo risultato"}'
        
        if self._is_on_target(u, goal):
            return '{"action":"done","text":"Pagina raggiunta","thought":"Obiettivo completato"}'
        
        return '{"action":"extract","thought":"Analizzo la pagina"}'

    def _find_direct_url(self, goal: str) -> str | None:
        if not self.KNOWN_SITES:
            return None
        for site, url in self.KNOWN_SITES.items():
            if site in goal:
                return url
        url_match = re.search(r'(https?://[^\s]+|[a-z0-9-]+\.[a-z]{2,})', goal)
        if url_match:
            found = url_match.group(1)
            if not found.startswith("http"):
                return f"https://{found}"
            return found
        return None
    
    def _is_on_target(self, page_content: str, goal: str) -> bool:
        if not goal:
            return False
        for site in (self.KNOWN_SITES or {}):
            if site in goal and site in page_content:
                return True
        return False

    def _smart_query(self, goal: str) -> str:
        clean = re.sub(r'\b(cerca|trova|apri|vai|dammi|fammi|vorrei|voglio|puoi|per favore)\b', '', goal, flags=re.I)
        clean = re.sub(r'\b(il|lo|la|i|gli|le|un|una|uno|di|a|da|in|su|per|con)\b', '', clean, flags=re.I)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean[:80] if clean else "ricerca"

    def warmup(self) -> None:
        pass


@dataclass
class HfLLM:
    model_id: str
    device: str = "auto"

    def __post_init__(self) -> None:
        self._tok: Any | None = None
        self._mdl: Any | None = None

    def _pick_device(self) -> str:
        import torch
        if self.device != "auto":
            return self.device
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        from huggingface_hub.errors import GatedRepoError

        dev = self._pick_device()
        dtype = torch.float16 if dev in {"cuda", "mps"} else torch.float32

        logger.info(f"Caricamento {self.model_id} su {dev}...")

        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
        try:
            tok = AutoTokenizer.from_pretrained(self.model_id, token=token)
            mdl = cast(
                Any,
                AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    dtype=dtype,
                    token=token,
                    low_cpu_mem_usage=True,
                ),
            )
        except (GatedRepoError, OSError) as e:
            if "gated repo" in str(e).lower() or "gatedrepoerror" in str(e).lower() or "401" in str(e):
                raise RuntimeError("hf_auth_required") from e
            raise

        mdl.to(dev)
        mdl.eval()
        self._tok = tok
        self._mdl = mdl
        logger.info("Modello caricato.")

    def warmup(self) -> None:
        if self._tok is None:
            self._load()

    def gen(self, sys: str, user: str) -> str:
        if self._tok is None or self._mdl is None:
            self._load()

        tok = cast(Any, self._tok)
        mdl = cast(Any, self._mdl)
        messages = [{"role": "system", "content": sys}, {"role": "user", "content": user}]

        try:
            try:
                prompt = tok.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True, enable_thinking=False,
                )
            except TypeError:
                prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        except Exception:
            prompt = sys + "\n\n" + user + "\n\nJSON:"

        inputs = tok(prompt, return_tensors="pt").to(mdl.device)
        input_len = inputs.input_ids.shape[1]
        out = mdl.generate(
            **inputs, max_new_tokens=160, do_sample=False, eos_token_id=tok.eos_token_id,
        )
        return str(tok.decode(out[0][input_len:], skip_special_tokens=True))
