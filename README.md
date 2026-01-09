GPT1 (modulo `ag`) è un agente di navigazione web che usa un LLM per decidere passo‑passo cosa fare nel browser a partire da istruzioni testuali. Il modello non “vede” screenshot: osserva lo stato corrente tramite URL/titolo e un estratto testuale della pagina che include una lista di elementi interattivi con selettori; in base a questo sceglie una singola azione alla volta (navigate/click/type/press/scroll/wait/extract/back/done) e il runtime la esegue nel browser.

L’esecuzione usa Playwright con Chromium gestito dall’app. Il cursore visibile in pagina è un overlay (cursore “disegnato” dentro la pagina) e, se abiliti l’opzione dedicata su macOS, può essere mosso anche il cursore di sistema per rendere il movimento evidente mentre l’agente opera.

Installazione con Python 3.10+:

```bash
python3 -m pip install -e ".[web,hf,dev]"
python3 -m playwright install chromium
```

Avvio in modalità chat (sessione persistente: memoria e contesto restano tra un tuo messaggio e il successivo):

```bash
python3 -m ag --hf --planner-mode model
```

Esecuzione “single goal” (stampa il JSON risultato):

```bash
python3 -m ag --hf --planner-mode model "trovami la pagina di OpenAI"
```

Per vedere meglio i passaggi durante la ricerca (niente salti “troppo rapidi”), usa demo mode e una pausa tra le azioni:

```bash
python3 -m ag --hf --planner-mode model --demo-mode --action-delay-ms 700
```

Per muovere anche il cursore di sistema su macOS (oltre all’overlay), abilita:

```bash
python3 -m ag --hf --planner-mode model --os-cursor
```

Su macOS questa opzione può richiedere permessi di “Accessibilità” o “Input Monitoring” per il Terminale/Python. Senza permessi l’agente può comunque navigare (mouse virtuale Playwright), ma il puntatore di sistema potrebbe non muoversi.

Opzioni CLI principali (tutte sono opzionali e hanno un equivalente via variabile d’ambiente):

```bash
--planner-mode model|hybrid
--headless / --no-headless
--auto-consent / --no-auto-consent
--os-cursor / --no-os-cursor
--demo-mode / --no-demo-mode
--action-delay-ms <int>
--plan-timeout-ms <int>
```

Variabili d’ambiente utili:

```bash
AG_MODEL_ID=Qwen/Qwen3-4B-Instruct-2507
AG_HF_DEVICE=auto
AG_MAX_STEPS=12
AG_TIMEOUT_MS=30000
AG_TEXT_BUDGET=6000
AG_MODEL_TEXT_BUDGET=3500
AG_PLAN_TIMEOUT_MS=180000
AG_DEMO_MODE=1
AG_ACTION_DELAY_MS=700
AG_OS_CURSOR=1
AG_HEADLESS=1
AG_AUTO_CONSENT=1
```

Nota sulle prestazioni: con un modello 4B in locale il tempo di pianificazione per step può variare da pochi secondi a decine di secondi, soprattutto su pagine molto lunghe o molto dinamiche (es. Google). Per evitare blocchi indefiniti esiste un timeout di pianificazione configurabile; se scatta, l’agente termina la richiesta corrente con un messaggio di timeout.

Per lo sviluppo: i test e i controlli del progetto sono eseguibili con:

```bash
python3 -m pytest -q
python3 -m ruff check .
python3 -m mypy ag
```
