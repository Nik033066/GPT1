from __future__ import annotations

# Browser
DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_TIMEOUT_MS = 30000

# Selectors
COOKIE_CONSENT_SELECTORS = [
    "button:has-text('Accetta')",
    "button:has-text('Accetto')",
    "button:has-text('Accetta tutto')",
    "button:has-text('Accetta tutti')",
    "button:has-text('I agree')",
    "button:has-text('Accept all')",
    "button:has-text('Accept')",
    "button#L2AGLb",  # Google 'Accept all' ID
    "button#QS5gu",   # Google 'Reject all' ID
    "div[role='dialog'] button:has-text('Accetta tutto')",
    "form[action*='consent'] button"
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

# JS Scripts
JS_HIDE_WEBDRIVER = """
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
"""

JS_EXTRACT_TEXT = """
    () => {
        function isVisible(e) {
            if (!e) return false;
            const style = window.getComputedStyle(e);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
            if (style.pointerEvents === 'none') return false;
            const rect = e.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        }

        function getSelector(e) {
            if (e.id) return '#' + CSS.escape(e.id);
            if (e.name) return `[name="${CSS.escape(e.name)}"]`;
            
            let sel = e.tagName.toLowerCase();
            if (e.className && typeof e.className === 'string') {
                const classes = e.className.split(/\s+/).filter(c => c.length > 0 && !c.match(/^[\d]/));
                if (classes.length > 0) sel += '.' + classes.map(c => CSS.escape(c)).join('.');
            }
            return sel;
        }

        let output = "--- ELEMENTI INTERATTIVI (Usa questi selettori) ---\\n";
        const elems = document.querySelectorAll('a, button, input, textarea, select, [role="button"], [role="link"], [role="menuitem"], [onclick], [tabindex]');
        
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
                if (img) {
                    text = img.getAttribute('alt') || "";
                }
            }
            if (!text) continue;

            output += `${count}. [${el.tagName}] "${text}" => ${getSelector(el)}\\n`;
            count++;
        }

        output += "\\n--- CONTENUTO TESTUALE ---\\n";
        const bodyText = document.body.innerText || "";
        output += bodyText.replace(/\\s+/g, ' ').slice(0, 1500);
        
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
    if (document.getElementById('ag-cursor')) return;
    
    const c = document.createElement('div');
    c.id = 'ag-cursor';
    c.style.position = 'fixed';
    c.style.width = '24px';
    c.style.height = '24px';
    c.style.zIndex = '2147483647';
    c.style.pointerEvents = 'none';
    c.style.transition = 'transform 0.08s cubic-bezier(0.2, 0.8, 0.2, 1)';
    c.style.transform = 'translate(-100px, -100px)';
    c.style.filter = 'drop-shadow(0 2px 4px rgba(0,0,0,0.4))';
    c.innerHTML = `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M5.5 3.5L11.5 19.5L14.5 13.5L20.5 13.5L5.5 3.5Z" fill="black" stroke="white" stroke-width="1.5" stroke-linejoin="round"/>
    </svg>
    `;
    document.body.appendChild(c);
    
    const s = document.createElement('div');
    s.id = 'ag-status';
    s.style.position = 'fixed';
    s.style.bottom = '20px';
    s.style.right = '20px';
    s.style.padding = '12px 20px';
    s.style.background = 'rgba(0, 0, 0, 0.85)';
    s.style.color = 'white';
    s.style.fontFamily = 'system-ui, -apple-system, sans-serif';
    s.style.fontSize = '14px';
    s.style.borderRadius = '8px';
    s.style.boxShadow = '0 4px 15px rgba(0,0,0,0.3)';
    s.style.zIndex = '2147483647';
    s.style.backdropFilter = 'blur(10px)';
    s.style.border = '1px solid rgba(255,255,255,0.1)';
    s.style.transition = 'opacity 0.3s ease';
    s.innerText = '🤖 Agente attivo';
    document.body.appendChild(s);
}"""

# LLM
SYSTEM_PROMPT = (
    "Sei un LLM Planner ingegneristico. Produci SOLO JSON valido, senza testo extra.\n"
    "Azioni ammesse: navigate, click, type, press, wait, extract, back, done.\n"
    "Regole:\n"
    "- Usa sempre doppi apici: JSON strict.\n"
    "- Usa selector CSS quando possibile.\n"
    "- Se devi cercare, usa: {\"action\":\"type\",\"selector\":\"input\",\"text\":\"...\"} poi {\"action\":\"press\",\"key\":\"Enter\"}.\n"
    "- Non inventare dati: se serve leggere, usa extract.\n"
    "- Se url è about:blank e l'obiettivo contiene un sito, fai navigate.\n"
    "- SE SEI SU GOOGLE SEARCH: Clicca sul primo risultato utile (spesso h3 o a > h3).\n"
    "Schema Act: {action, url?, selector?, text?, key?, ms?, field?}.\n"
    "Esempi:\n"
    "{\"action\":\"navigate\",\"url\":\"https://www.google.com\"}\n"
    "{\"action\":\"click\",\"selector\":\"h3\"}\n"
    "{\"action\":\"done\",\"text\":\"...\"}\n"
)
