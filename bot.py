"""
Bot di assistenza SnazzyLines su Telegram.

PERCHE E STATO RIFATTO (2026-08-17)
Il difetto grave, verificato confrontando la versione precedente col negozio vero:
i prezzi dei pacchetti erano incollati dentro il testo di sistema, quindi non si
aggiornavano mai. Il negozio nel frattempo e andato in saldo e i due si sono
scollati: il pacchetto da 70 fornitori veniva annunciato a 12,99 € mentre in
cassa ne costava 9,99. Il bot dichiarava cifre piu ALTE del vero, cioe scoraggiava
l acquisto da solo. E per gli articoli fuori dal listino di Bruno (una marca
precisa, una borsa, un orologio) si inventava numeri di sana pianta, perche a un
modello a cui si chiede "quanto costa" il buco lo riempie sempre.

COME SONO STATI RISOLTI, senza sperare nella buona volonta del modello:
- I prezzi dei pacchetti si leggono dal negozio vero, non stanno nel codice.
  L endpoint e quello pubblico di Shopify, quindi in questo repo (che e pubblico)
  non entra nessuna credenziale.
- Il listino della merce e un blocco di testo di Bruno, inviato parola per parola.
- CONTROLLO IN USCITA: prima di inviare, il codice estrae dalla risposta ogni
  cifra che sta in un contesto di prezzo e la confronta con i numeri consentiti.
  Se compare un prezzo che non e di Bruno, quel messaggio NON parte e al suo
  posto va la risposta fissa che rimanda alla chat diretta. Il modello puo anche
  inventare: non arriva al cliente.
"""

import os
import re
import json
import time
import logging
import urllib.request
import urllib.error

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic

# ─── Configurazione ──────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Haiku e non Sonnet: e un bot che risponde a domande frequenti con un prompt
# fisso, e chiunque puo scrivergli. Sonnet qui sarebbe soldi buttati.
#
# Nome corto senza la data in fondo, di proposito. La versione precedente puntava
# a un modello con la data attaccata: quel modello e stato dismesso il 16/08/2026
# e da quel giorno il bot rispondeva "ho avuto un problema tecnico" a chiunque,
# senza che nessun errore fosse visibile da fuori. Il nome corto segue da solo la
# versione buona e non scade di colpo.
MODELLO = "claude-haiku-4-5"

CHAT_DIRETTA = "@snazzylines"
SITO = "snazzylines.store"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ─── Listino merce: fonte unica, si invia parola per parola ───────────────────
# Sono stime di Bruno, nessuna API le conosce. Il modello non deve riformularle
# ne estenderle ad altre categorie.
LISTINO_MERCE = (
    "Prezzi indicativi dai fornitori:\n"
    "• Scarpe: 30-80 €\n"
    "• Maglie: 10-15 €\n"
    "• Maglie da calcio: 10-15 €\n"
    "• Giubbotti: 30-50 €\n"
    "• Pantaloni: 10-20 €\n"
    "• Felpe: 10-15 €\n"
    "• Accessori: 10-30 €"
)

# Categorie coperte dal listino. Tutto il resto e "fuori elenco".
CATEGORIE_NOTE = ("scarpe", "maglie", "maglietta", "magliette", "calcio", "giubbotti",
                  "giubbotto", "pantaloni", "felpe", "felpa", "accessori", "accessorio")

RISPOSTA_FUORI_ELENCO = (
    "Su quell'articolo non ho un prezzo da darti: dipende dal fornitore e dal momento, "
    "e lo vedi direttamente nel suo catalogo.\n\n"
    f"{LISTINO_MERCE}\n\n"
    f"Per una risposta precisa scrivi su {CHAT_DIRETTA}, ti rispondono direttamente."
)

RIMANDA_ALLA_CHAT = (
    f"Su questo ti conviene scrivere direttamente su {CHAT_DIRETTA}: "
    "ti rispondono loro con precisione."
)

# ─── Prezzi dei pacchetti: letti dal negozio, non scritti qui ─────────────────
PRODOTTI_URL = f"https://{SITO}/products.json?limit=250"
# Le etichette ricalcano i titoli veri dei prodotti sul negozio (verificati il
# 2026-08-17). Se in negozio cambia cosa contiene un pacchetto, si aggiorna qui:
# il prezzo si aggiorna da solo, il contenuto no.
PACCHETTI = {
    "basic-pack": "70 contatti fornitori",
    "pro-pack": "100 contatti fornitori",
    "premium-pack": "150 contatti fornitori + Guida",
    "ultimate-pack": "1000+ contatti fornitori + Guida + bot Vinted",
}
DURATA_CACHE = 3600  # un'ora: cambi un prezzo in negozio e il bot si allinea da solo
_cache = {"quando": 0.0, "testo": "", "numeri": set()}


def _leggi_pacchetti():
    """Ritorna (testo per il prompt, insieme dei prezzi) letti dal negozio."""
    richiesta = urllib.request.Request(PRODOTTI_URL, headers={"User-Agent": "SnazzyLinesBot/1.0"})
    with urllib.request.urlopen(richiesta, timeout=12) as risposta:
        dati = json.loads(risposta.read().decode("utf-8"))

    trovati = []
    for prodotto in dati.get("products", []):
        handle = prodotto.get("handle")
        if handle not in PACCHETTI:
            continue
        varianti = prodotto.get("variants") or []
        if not varianti:
            continue
        prezzo = float(varianti[0]["price"])
        precedente = varianti[0].get("compare_at_price")
        trovati.append((prezzo, PACCHETTI[handle], float(precedente) if precedente else None))

    if not trovati:
        raise ValueError("nessun pacchetto trovato nel negozio")

    trovati.sort(key=lambda x: x[0])
    righe, numeri = [], set()
    for prezzo, etichetta, precedente in trovati:
        riga = f"• {etichetta}: {prezzo:.2f} €".replace(".", ",")
        if precedente:
            riga += f" (invece di {precedente:.2f} €)".replace(".", ",")
            numeri.add(round(precedente, 2))
        righe.append(riga)
        numeri.add(round(prezzo, 2))
    return "\n".join(righe), numeri


def pacchetti_correnti():
    """Come sopra, con cache. Se il negozio non risponde tiene l'ultimo valore
    buono invece di inventare: meglio un prezzo di un'ora fa che uno sbagliato."""
    adesso = time.time()
    if _cache["testo"] and adesso - _cache["quando"] < DURATA_CACHE:
        return _cache["testo"], _cache["numeri"]
    try:
        testo, numeri = _leggi_pacchetti()
        _cache.update({"quando": adesso, "testo": testo, "numeri": numeri})
    except Exception as errore:
        log.error("lettura prezzi dal negozio fallita: %s", errore)
        if not _cache["testo"]:
            raise
    return _cache["testo"], _cache["numeri"]


# ─── Controllo in uscita: nessuna cifra che non sia di Bruno ──────────────────
# Numeri ammessi oltre ai prezzi dei pacchetti: gli estremi degli intervalli del
# listino merce. Sono gli unici prezzi che il bot ha il diritto di pronunciare.
NUMERI_LISTINO = {10.0, 15.0, 20.0, 30.0, 50.0, 80.0}

# Cerca cifre in CONTESTO DI PREZZO: con simbolo/parola euro accanto, oppure in
# un intervallo tipo "30-80". Non guarda i numeri normali di una frase, cosi
# "meno di 1 minuto" o "oltre 200 recensioni" non fanno scattare nulla.
_PREZZI = re.compile(
    r"€\s*(\d{1,4}(?:[.,]\d{1,2})?)"
    r"|(\d{1,4}(?:[.,]\d{1,2})?)\s*(?:€|eur\b|euro\b)"
    r"|(\d{1,4})\s*[-–a]\s*(\d{1,4})\s*(?:€|eur\b|euro\b)",
    re.IGNORECASE,
)


def cifre_di_prezzo(testo):
    trovate = []
    for gruppi in _PREZZI.findall(testo):
        for valore in gruppi:
            if not valore:
                continue
            try:
                trovate.append(round(float(valore.replace(",", ".")), 2))
            except ValueError:
                pass
    return trovate


def risposta_ammessa(testo, numeri_pacchetti):
    """False se il testo contiene un prezzo che non e nostro."""
    consentiti = set(numeri_pacchetti) | NUMERI_LISTINO
    for cifra in cifre_di_prezzo(testo):
        if cifra not in consentiti:
            log.warning("risposta bloccata: prezzo non consentito %.2f", cifra)
            return False
    return True


# ─── Prompt ──────────────────────────────────────────────────────────────────
def costruisci_prompt(testo_pacchetti):
    return f"""Sei l'assistente di SnazzyLines. Rispondi sempre in italiano, cordiale e diretto, frasi corte, mai muri di testo.

COSA VENDIAMO
Pacchetti digitali in PDF con contatti di fornitori verificati all'ingrosso (abbigliamento, scarpe, accessori). Non vendiamo capi: vendiamo l'accesso ai fornitori. Dopo il pagamento il PDF arriva via email in meno di un minuto.

PACCHETTI E PREZZI
{testo_pacchetti}

{LISTINO_MERCE}

COME FUNZIONA
Il cliente sceglie il pacchetto sul sito {SITO}, paga, riceve subito il PDF via email, dentro trova i contatti dei fornitori (link ai siti e numeri WhatsApp) e ordina direttamente da loro.

COSA E VERO DI OGNI PACCHETTO
- In ogni pacchetto e incluso un fornitore italiano che lavora col pagamento alla consegna: si paga la merce quando arriva a casa. Riguarda l'ordine al fornitore, non l'acquisto del pacchetto.
- Non serve la P.IVA e non c'e un ordine minimo: si puo ordinare anche un pezzo solo.
- Il PDF arriva via email in meno di un minuto dall'acquisto.

REGOLA PIU IMPORTANTE
Non dire MAI un prezzo che non sia scritto qui sopra. Se ti chiedono il prezzo di un articolo che non e nel listino (per esempio una marca precisa, una borsa, un orologio, un profumo), NON stimare e NON inventare: di' che dipende dal fornitore e si vede nel suo catalogo, e rimanda a {CHAT_DIRETTA}.

ALTRE REGOLE
- Se la risposta non e in questo documento, dillo e rimanda a {CHAT_DIRETTA}. Non ricostruirla a intuito.
- Non elencare marche a memoria e non promettere quali marche si trovano.
- Non fare promesse di guadagno.
- Non usare le parole replica, falso, contraffatto, 1:1.
- Rimborsi: non entrare nel merito, rimanda a {CHAT_DIRETTA}.
- Se chiedono le recensioni: sono nei commenti sotto i video TikTok @snazzylines.
- Se la domanda non riguarda SnazzyLines: una riga e riporta il discorso sul servizio.
- Se qualcuno e aggressivo, resta gentile."""


# ─── Anthropic ───────────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

MAX_STORICO = 12
MAX_UTENTI = 500  # oltre questo si buttano i piu vecchi: prima cresceva all'infinito
conversazioni = {}
ultimo_uso = {}

# Limite di richieste: il bot e pubblico e ogni messaggio e una chiamata a
# pagamento. Senza questo, una sola persona annoiata puo prosciugare il credito.
MAX_AL_MINUTO = 6
MAX_ALL_ORA = 40
richieste = {}


def entro_i_limiti(utente):
    adesso = time.time()
    segnate = [t for t in richieste.get(utente, []) if adesso - t < 3600]
    ultimo_minuto = [t for t in segnate if adesso - t < 60]
    if len(ultimo_minuto) >= MAX_AL_MINUTO or len(segnate) >= MAX_ALL_ORA:
        richieste[utente] = segnate
        return False
    segnate.append(adesso)
    richieste[utente] = segnate
    return True


def libera_memoria():
    if len(conversazioni) <= MAX_UTENTI:
        return
    vecchi = sorted(ultimo_uso.items(), key=lambda x: x[1])[: len(conversazioni) - MAX_UTENTI]
    for utente, _ in vecchi:
        conversazioni.pop(utente, None)
        ultimo_uso.pop(utente, None)


def chiedi_a_claude(utente, messaggio):
    try:
        testo_pacchetti, numeri = pacchetti_correnti()
    except Exception:
        return RIMANDA_ALLA_CHAT, True

    conversazioni.setdefault(utente, [])
    conversazioni[utente].append({"role": "user", "content": messaggio})
    conversazioni[utente] = conversazioni[utente][-MAX_STORICO:]
    ultimo_uso[utente] = time.time()
    libera_memoria()

    try:
        risposta = client.messages.create(
            model=MODELLO,
            max_tokens=400,
            system=costruisci_prompt(testo_pacchetti),
            messages=conversazioni[utente],
        )
        testo = risposta.content[0].text.strip()
    except Exception as errore:
        log.error("chiamata ad Anthropic fallita: %s", errore)
        conversazioni[utente].pop()
        return RIMANDA_ALLA_CHAT, True

    # Qui sta la garanzia: se e uscito un prezzo che non e nostro, non parte.
    if not risposta_ammessa(testo, numeri):
        conversazioni[utente].pop()
        return RISPOSTA_FUORI_ELENCO, True

    conversazioni[utente].append({"role": "assistant", "content": testo})
    return testo, False


# ─── Comandi ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ciao, sono l'assistente di SnazzyLines.\n\n"
        "Posso dirti quali pacchetti abbiamo, quanto costano, come funziona la consegna "
        "e che prezzi trovi di solito dai fornitori.\n\n"
        f"Per richieste specifiche ti rimando alla chat diretta {CHAT_DIRETTA}.\n\n"
        "Scrivimi pure."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    utente = update.effective_user.id
    conversazioni.pop(utente, None)
    ultimo_uso.pop(utente, None)
    await update.message.reply_text("Conversazione azzerata, scrivimi pure.")


async def prezzi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Risposta senza modello: solo dati veri, zero possibilita di sbagliare."""
    try:
        testo_pacchetti, _ = pacchetti_correnti()
        await update.message.reply_text(f"I nostri pacchetti:\n{testo_pacchetti}\n\n{LISTINO_MERCE}")
    except Exception:
        await update.message.reply_text(RIMANDA_ALLA_CHAT)


async def messaggio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    utente = update.effective_user.id
    if not entro_i_limiti(utente):
        await update.message.reply_text(
            "Stai scrivendo un po' troppo in fretta, aspetta un minuto.\n\n"
            f"Se hai qualcosa di urgente scrivi su {CHAT_DIRETTA}."
        )
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    testo, _ = chiedi_a_claude(utente, update.message.text)
    await update.message.reply_text(testo)


def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN non impostato")
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY non impostato")

    try:
        testo, numeri = pacchetti_correnti()
        log.info("prezzi letti dal negozio all'avvio:\n%s", testo)
    except Exception as errore:
        log.error("prezzi non leggibili all'avvio: %s", errore)

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("prezzi", prezzi))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messaggio))

    log.info("Bot SnazzyLines avviato con modello %s", MODELLO)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
