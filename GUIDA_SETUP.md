# SnazzyLines Bot — Guida Setup

## Cosa ti serve:
1. ✅ Bot Telegram (FATTO — @Assistenza_SnazzyLines_bot)
2. 🔑 API Key di Anthropic (Claude)
3. 🚀 Account Railway (gratuito) per hosting

---

## STEP 1 — Prendi la API Key di Anthropic

1. Vai su https://console.anthropic.com
2. Registrati (o accedi)
3. Vai su "API Keys"
4. Clicca "Create Key"
5. Copia la key (inizia con "sk-ant-...")
6. Ricarica il credito: anche solo $5 bastano per MESI

---

## STEP 2 — Crea account Railway

1. Vai su https://railway.app
2. Registrati con GitHub (se non hai GitHub, crealo prima su github.com)
3. Railway ti dà $5 di credito gratis al mese — bastano per il bot

---

## STEP 3 — Carica il bot su GitHub

1. Vai su https://github.com/new
2. Nome repository: "snazzylines-bot"
3. Clicca "Create repository"
4. Carica TUTTI i file di questa cartella (bot.py, requirements.txt, Procfile, nixpacks.toml)
5. Clicca "Commit changes"

---

## STEP 4 — Deploy su Railway

1. Vai su https://railway.app/new
2. Clicca "Deploy from GitHub repo"
3. Seleziona "snazzylines-bot"
4. Railway inizia a fare il deploy automaticamente

---

## STEP 5 — Imposta le variabili d'ambiente

1. Su Railway, clicca sul tuo progetto
2. Vai su "Variables"
3. Aggiungi queste 2 variabili:

   TELEGRAM_TOKEN = 8049647029:AAEIYksdtWlUIVZxUb7QR17nyAVUsxpvbnk
   ANTHROPIC_API_KEY = (la tua key sk-ant-...)

4. Railway si riavvia automaticamente

---

## STEP 6 — Testa il bot!

1. Apri Telegram
2. Cerca @Assistenza_SnazzyLines_bot
3. Scrivi /start
4. Fai una domanda tipo "quanto costano i pacchetti?"
5. Se risponde, SEI LIVE! 🔥

---

## Costi mensili:
- Railway: GRATIS (piano gratuito basta)
- Anthropic API: ~€5-15/mese (dipende dal volume messaggi)
- TOTALE: ~€5-15/mese

---

## Comandi del bot:
- /start — Messaggio di benvenuto
- /reset — Resetta la conversazione

---

## Se qualcosa non va:
- Controlla le variabili d'ambiente su Railway
- Guarda i log su Railway (clicca "Deployments" → "View Logs")
- Scrivimi su Claude e risolviamo!
