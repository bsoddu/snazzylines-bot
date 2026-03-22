import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

logging.basicConfig(level=logging.INFO)

SYSTEM = "Sei l'assistente virtuale di SnazzyLines, servizio italiano che vende pacchetti di contatti fornitori verificati. Rispondi SEMPRE in italiano, tono giovane e diretto. Risposte brevi. PACCHETTI: BASIC 70 contatti 9.99 euro, PRO 100 contatti 12.99 euro, PREMIUM 150 contatti + Guida Resell 15.99 euro, ULTIMATE 1000+ contatti + Guida Resell 19.99 euro. PREZZI FORNITORI: Scarpe 30-80 euro, Maglie 6-10, Maglie calcio 10-15, Giubbotti 30-50, Pantaloni 10-20, Felpe 10-15, Accessori 10-30. COME FUNZIONA: Compri sul sito, ricevi PDF via email in 1 minuto, dentro trovi link ai fornitori. Brand: Nike, Adidas, Ralph Lauren, TNF, Stone Island, Moncler, Burberry, Lacoste. 200+ recensioni reali su TikTok. Sito: snazzylines.store. Supporto: @snazzylines. Mai dire replica o 1:1. Mai promesse di guadagno."

genai.configure(api_key=GEMINI_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ciao! Sono l'assistente di SnazzyLines.\n\nPosso aiutarti con:\n- Info sui pacchetti e prezzi\n- Come funziona il servizio\n- Prezzi medi dai fornitori\n\nScrivimi pure!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
       model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(SYSTEM + "\n\nCliente dice: " + update.message.text + "\n\nRispondi al cliente:")
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"DEBUG ERRORE: {str(e)}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Reset! Scrivimi pure")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
