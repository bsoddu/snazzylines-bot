import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM = """Sei l'assistente virtuale di SnazzyLines, un servizio italiano che vende pacchetti di contatti fornitori verificati. Rispondi SEMPRE in italiano, tono giovane, amichevole e diretto. Risposte brevi.

PACCHETTI: BASIC 70 contatti €9.99 | PRO 100 contatti €12.99 | PREMIUM 150 contatti + Guida Resell €15.99 | ULTIMATE 1000+ contatti + Guida Resell €19.99

PREZZI FORNITORI: Scarpe €30-80 | Maglie €6-10 | Maglie calcio €10-15 | Giubbotti €30-50 | Pantaloni €10-20 | Felpe €10-15 | Accessori €10-30

COME FUNZIONA: Compri sul sito → ricevi PDF via email in meno di 1 minuto → dentro trovi i link ai fornitori → contatti e ordini.

Brand: Nike, Adidas, Ralph Lauren, TNF, Stone Island, Moncler, Burberry, Lacoste e altri. NON vendiamo vestiti, vendiamo ACCESSO ai fornitori. 200+ recensioni reali su TikTok @snazzylines. Sito: snazzylines.store. Supporto: @snazzylines su Telegram. Mai dire replica o 1:1. Mai promesse di guadagno. Se non sai qualcosa rimanda a @snazzylines."""

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ciao! 👋 Sono l'assistente di SnazzyLines.\n\nPosso aiutarti con:\n• Info sui pacchetti e prezzi\n• Come funziona il servizio\n• Prezzi medi dai fornitori\n\nScrivimi pure! 🔥")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        response = model.generate_content(f"{SYSTEM}\n\nCliente: {user_message}\n\nRispondi:")
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error(f"Errore: {e}")
        await update.message.reply_text("Scusa, riprova tra un attimo o scrivi a @snazzylines!")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Conversazione resettata! Scrivimi pure 😊")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot avviato!")
    app.run_polling()

if __name__ == "__main__":
    main()
