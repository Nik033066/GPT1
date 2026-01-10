from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Cfg:
    """
    Configurazione dell'agente.
    Il CURSORE REALE del Mac è sempre attivo (non c'è più un cursore virtuale).
    """
    # === Modello LLM ===
    model_id: str = os.environ.get("AG_MODEL_ID", "Qwen/Qwen3-4B-Instruct-2507")
    hf_device: str = os.environ.get("AG_HF_DEVICE", "auto")
    
    # === Esecuzione ===
    max_steps: int = int(os.environ.get("AG_MAX_STEPS", "12"))
    page_timeout_ms: int = int(os.environ.get("AG_TIMEOUT_MS", "30000"))
    text_budget: int = int(os.environ.get("AG_TEXT_BUDGET", "6000"))
    model_text_budget: int = int(os.environ.get("AG_MODEL_TEXT_BUDGET", "3500"))
    plan_timeout_ms: int = int(os.environ.get("AG_PLAN_TIMEOUT_MS", "180000"))
    planner_mode: str = os.environ.get("AG_PLANNER_MODE", "hybrid")
    
    # === Browser ===
    auto_consent: bool = os.environ.get("AG_AUTO_CONSENT", "1").strip() in {"1", "true", "True", "yes", "YES"}
    headless: bool = os.environ.get("AG_HEADLESS", "0").strip() in {"1", "true", "True", "yes", "YES"}
    browser: str = os.environ.get("AG_BROWSER", "chromium")
    cdp_url: str = os.environ.get("AG_CDP_URL", "")
    browser_app: str = os.environ.get("AG_BROWSER_APP", "")
    
    # === Animazione ===
    action_delay_ms: int = int(os.environ.get("AG_ACTION_DELAY_MS", "0"))
    demo_mode: bool = os.environ.get("AG_DEMO_MODE", "1").strip() in {"1", "true", "True", "yes", "YES"}
