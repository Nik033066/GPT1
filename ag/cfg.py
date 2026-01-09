from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Cfg:
    model_id: str = os.environ.get("AG_MODEL_ID", "Qwen/Qwen3-4B-Instruct-2507")
    hf_device: str = os.environ.get("AG_HF_DEVICE", "auto")
    max_steps: int = int(os.environ.get("AG_MAX_STEPS", "12"))
    page_timeout_ms: int = int(os.environ.get("AG_TIMEOUT_MS", "30000"))
    text_budget: int = int(os.environ.get("AG_TEXT_BUDGET", "6000"))
    model_text_budget: int = int(os.environ.get("AG_MODEL_TEXT_BUDGET", "3500"))
    plan_timeout_ms: int = int(os.environ.get("AG_PLAN_TIMEOUT_MS", "180000"))
    planner_mode: str = os.environ.get("AG_PLANNER_MODE", "model")
    auto_consent: bool = os.environ.get("AG_AUTO_CONSENT", "0").strip() in {"1", "true", "True", "yes", "YES"}
    headless: bool = os.environ.get("AG_HEADLESS", "0").strip() in {"1", "true", "True", "yes", "YES"}
    os_cursor: bool = os.environ.get("AG_OS_CURSOR", "0").strip() in {"1", "true", "True", "yes", "YES"}
    action_delay_ms: int = int(os.environ.get("AG_ACTION_DELAY_MS", "0"))
    demo_mode: bool = os.environ.get("AG_DEMO_MODE", "0").strip() in {"1", "true", "True", "yes", "YES"}
    browser: str = os.environ.get("AG_BROWSER", "chromium")
    cdp_url: str = os.environ.get("AG_CDP_URL", "")
    browser_app: str = os.environ.get("AG_BROWSER_APP", "")
