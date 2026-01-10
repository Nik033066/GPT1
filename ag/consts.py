from __future__ import annotations

import json
import os
from typing import Dict

DEFAULT_CDP_URL = os.environ.get("AG_CDP_URL_DEFAULT", "http://127.0.0.1:9222")
DEFAULT_TIMEOUT_MS = 30000

# URL configurabili per evitare valori hardcoded nelle strategie
DEFAULT_HOME_URL = os.environ.get("AG_HOME_URL", "https://google.com")
ALT_SEARCH_URL = os.environ.get("AG_ALT_URL", "https://www.bing.com")
DEFAULT_TARGET_SITE = os.environ.get("AG_TARGET_SITE", "https://openai.com")
EXAMPLE_ARTICLE_URL = os.environ.get("AG_EXAMPLE_ARTICLE_URL", "https://example.com/article")
ALT_NEWS_URL = os.environ.get("AG_ALT_NEWS_URL", "https://news.google.com")
ALT_QUERY_BASE = os.environ.get("AG_ALT_QUERY_BASE", "https://duckduckgo.com/?q=")
BOOT_GITHUB_URL = os.environ.get("AG_BOOT_GITHUB_URL", "https://github.com/test")

def _load_known_sites() -> Dict[str, str]:
    raw = os.environ.get("AG_KNOWN_SITES", "")
    if raw:
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in obj.items()):
                return obj
        except Exception:
            pass
    return {
        "openai": "https://openai.com",
        "google": "https://google.com",
        "github": "https://github.com",
        "wikipedia": "https://wikipedia.org",
        "youtube": "https://youtube.com",
        "twitter": "https://twitter.com",
        "x.com": "https://x.com",
        "linkedin": "https://linkedin.com",
        "facebook": "https://facebook.com",
        "reddit": "https://reddit.com",
        "amazon": "https://amazon.com",
        "stackoverflow": "https://stackoverflow.com",
    }

KNOWN_SITES = _load_known_sites()

COOKIE_CONSENT_SELECTORS = [
    "button:has-text('Accetta')",
    "button:has-text('Accept')",
    "button:has-text('Agree')",
    "button:has-text('OK')",
    "button:has-text('Acconsento')",
    "button:has-text('I agree')",
    "[role='dialog'] button",
    "form[action*='consent'] button",
    "#bnp_btn_accept",  # Bing
    "#L2AGLb",          # Google
    "button[id*='accept']",
    "button[id*='consent']",
]

MAC_BROWSER_APPS = [
    ("bundle", "com.google.Chrome"),
    ("bundle", "com.google.Chrome.canary"),
    ("bundle", "org.chromium.Chromium"),
    ("bundle", "com.brave.Browser"),
    ("bundle", "com.microsoft.edgemac"),
    ("bundle", "company.thebrowser.Browser"),
    ("app", "Google Chrome"),
    ("app", "Google Chrome Canary"),
    ("app", "Chromium"),
    ("app", "Brave Browser"),
    ("app", "Microsoft Edge"),
    ("app", "Arc"),
]

MAC_EXCLUDED_APPS = {
    "ChatGPT Atlas",
    "com.openai.atlas",
    "/Applications/ChatGPT Atlas.app"
}

JS_HIDE_WEBDRIVER = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
"""

JS_EXTRACT_TEXT = """
    () => {
        function isVisible(e) {
            if (!e) return false;
            const style = window.getComputedStyle(e);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
            const rect = e.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        }

        function getSelector(e) {
            if (e.id) return '#' + CSS.escape(e.id);
            if (e.name) return `[name="${CSS.escape(e.name)}"]`;
            let sel = e.tagName.toLowerCase();
            if (e.className && typeof e.className === 'string') {
                const classes = e.className.split(/\\s+/).filter(c => c.length > 0 && !c.match(/^[\\d]/));
                if (classes.length > 0) sel += '.' + classes.map(c => CSS.escape(c)).join('.');
            }
            return sel;
        }

        let output = "--- ELEMENTI INTERATTIVI ---\\n";
        const elems = document.querySelectorAll('a, button, input, textarea, select, [role="button"], [role="link"], [onclick], [tabindex]');
        
        let count = 0;
        for (const el of elems) {
            if (!isVisible(el)) continue;
            if (count > 150) break;
            if (el.hasAttribute && el.hasAttribute('disabled')) continue;

            let text = (el.innerText || el.value || el.getAttribute('aria-label') || "").replace(/\\s+/g, ' ').trim();
            if (text.length > 50) text = text.slice(0, 50) + "...";
            
            if (!text && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                text = "[Input " + (el.placeholder || "") + "]";
            }
            if (!text && el.tagName === 'A') {
                const img = el.querySelector('img');
                if (img) text = img.getAttribute('alt') || "";
            }
            if (!text) continue;

            output += `${count}. [${el.tagName}] "${text}" => ${getSelector(el)}\\n`;
            count++;
        }

        output += "\\n--- CONTENUTO ---\\n";
        output += (document.body.innerText || "").replace(/\\s+/g, ' ').slice(0, 1500);
        return output;
    }
"""

JS_GET_SCREEN_OFFSET = """
    () => {
        const tb = window.outerHeight - window.innerHeight;
        return [window.screenX, window.screenY + tb];
    }
"""

JS_INSTALL_CURSOR = """() => {
    if (document.getElementById('ag-status')) return;
    const s = document.createElement('div');
    s.id = 'ag-status';
    s.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:10px 14px;background:rgba(0,0,0,0.65);color:white;font-family:system-ui;font-size:13px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.25);z-index:2147483647;backdrop-filter:blur(8px)';
    s.innerText = '●';
    document.body.appendChild(s);
    window.__agSetStatus = (msg) => {
        const el = document.getElementById('ag-status');
        if (el) el.innerText = msg || '●';
    };
}"""
