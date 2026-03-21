import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic

# === CONFIG ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# === SYSTEM PROMPT ===
SYSTEM_PROMPT = """Sei l'assistente virtuale di SnazzyLines, un servizio italiano che vende pacchetti di contatti fornitori verificati per abbigliamento, scarpe, accessori e altro. Rispondi SEMPRE in italiano, in modo amichevole, diretto e professionale. Usa un tono giovane ma affidabile.

INFORMAZIONI SU SNAZZYLINES:

COSA VENDIAMO:
- Pacchetti digitali (PDF) contenenti contatti di fornitori verificati all'ingrosso
- Dopo l'acquisto il cliente riceve il PDF via email istantaneamente (meno di 1 minuto)
- I fornitori vendono capi firmati, vintage, streetwear e altro a prezzi all'ingrosso
- Non vendiamo vestiti direttamente — vendiamo l'ACCESSO ai fornitori

I NOSTRI PACCHETTI:
1. BASIC — 70 contatti fornitori → €9.99
2. PRO — 100 contatti fornitori → €12.99
3. PREMIUM — 150 contatti + Guida Resell → €15.99
4. ULTIMATE — 1000+ contatti + Guida Resell → €19.99

LISTINO PREZZI MEDI DAI FORNITORI:
- Scarpe: €30-80
- Maglie: €6-10
- Maglie da calcio: €10-15
- Giubbotti: €30-50
- Pantaloni: €10-20
- Felpe: €10-15
- Accessori: €10-30

COME FUNZIONA:
1. Il cliente sceglie il pacchetto sul sito
2. Paga con carta, PayPal, Apple Pay, Google Pay
3. Riceve ISTANTANEAMENTE il PDF via email
4. Apre il PDF e trova tutti i link ai fornitori
5. Contatta i fornitori e ordina quello che vuole

FAQ COMUNI:
- "È affidabile?" → Sì, abbiamo oltre 200 recensioni reali verificabili su TikTok
- "Posso vedere le recensioni?" → Sì, guarda i commenti sotto i nostri video TikTok @snazzylines
- "C'è un minimo d'ordine?" → Dipende dal fornitore, la maggior parte non ha minimo
- "Come ricevo il pacchetto?" → Via email, istantaneamente dopo il pagamento
- "Posso avere un rimborso?" → I prodotti digitali non sono rimborsabili, ma se hai problemi scrivici
- "Che brand ci sono?" → Nike, Adidas, Ralph Lauren, The North Face, Stone Island, Moncler, Burberry, Lacoste e molti altri
- "Vendete roba falsa/replica?" → NO. I nostri fornitori vendono prodotti autentici a prezzi all'ingrosso, vintage e stock

LINK UTILI:
- Sito: snazzylines.store
- TikTok: @snazzylines
- Telegram: @snazzylines

REGOLE IMPORTANTI:
1. Non inventare MAI informazioni che non hai
2. Se non sai rispondere a qualcosa di specifico, dì: "Per questa domanda ti consiglio di scrivere direttamente a @snazzylines su Telegram, ti risponderanno il prima possibile!"
3. Non discutere mai di rimborsi in dettaglio — rimanda sempre a @snazzylines
4. Non fare promesse di guadagno
5. Non usare parole come "replica", "1:1", "contraffatto"
6. Sii conciso — risposte brevi e dirette, non muri di testo
7. Se qualcuno chiede il link diretto al sito, mandalo a snazzylines.store
8. Se qualcuno è scortese o aggressivo, resta gentile e professionale
9. Se qualcuno chiede cose non relative a SnazzyLines, rispondi brevemente e riporta la conversazione sul servizio
"""

# === ANTHROPIC CLIENT ===
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Store conversation history per user (in memory)
conversations = {}
MAX_HISTORY = 20  # max messages to keep per user

async def get_ai_response(user_id: int, user_message: str) -> str:
    """Get response from Claude"""
    
    # Init or get conversation history
    if user_id not in conversations:
        conversations[user_id] = []
    
    # Add user message
    conversations[user_id].append({"role": "user", "content": user_message})
    
    # Keep only last N messages
    if len(conversations[user_id]) > MAX_HISTORY:
        conversations[user_id] = conversations[user_id][-MAX_HISTORY:]
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=conversations[user_id]
        )
        
        assistant_message = response.content[0].text
        
        # Add assistant response to history
        conversations[user_id].append({"role": "assistant", "content": assistant_message})
        
        return assistant_message
    
    except Exception as e:
        logger.error(f"Anthropic API error: {e}")
        return "Scusa, ho avuto un problema tecnico. Riprova tra un attimo o scrivi direttamente a @snazzylines!"

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome = (
        "Ciao! 👋 Sono l'assistente di SnazzyLines.\n\n"
        "Posso aiutarti con:\n"
        "• Info sui pacchetti e prezzi\n"
        "• Come funziona il servizio\n"
        "• Prezzi medi dai fornitori\n"
        "• Qualsiasi domanda su SnazzyLines\n\n"
        "Scrivimi pure, sono qui per te! 🔥"
    )
    await update.message.reply_text(welcome)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    user_message = update.message.text
    user_id = update.effective_user.id
    
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Get AI response
    response = await get_ai_response(user_id, user_message)
    
    await update.message.reply_text(response)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset conversation history"""
    user_id = update.effective_user.id
    conversations.pop(user_id, None)
    await update.message.reply_text("Conversazione resettata! Scrivimi pure 😊")

# === MAIN ===
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN non impostato!")
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY non impostato!")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot SnazzyLines avviato!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
