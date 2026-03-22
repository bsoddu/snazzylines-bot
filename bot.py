import os
import logging
import requests
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO)

SYSTEM = """Sei l'assistente virtuale di SnazzyLines, un servizio italiano che vende pacchetti di contatti fornitori verificati per abbigliamento, scarpe, accessori e altro. Rispondi SEMPRE in italiano, in modo amichevole, diretto e professionale. Usa un tono giovane ma affidabile. Usa emoji nelle risposte per renderle piu coinvolgenti. Dai risposte complete e dettagliate, non troppo corte. Struttura le risposte in modo chiaro con emoji come bullet points.

INFORMAZIONI SU SNAZZYLINES:

COSA VENDIAMO:
- Pacchetti digitali (PDF) contenenti contatti di fornitori verificati all'ingrosso
- Dopo l'acquisto il cliente riceve il PDF via email istantaneamente (meno di 1 minuto)
- I fornitori vendono capi firmati, vintage, streetwear e altro a prezzi all'ingrosso
- Non vendiamo vestiti direttamente, vendiamo l'ACCESSO ai fornitori

I NOSTRI PACCHETTI:
1. BASIC - 70 contatti fornitori - 9.99 euro
2. PRO - 100 contatti fornitori - 12.99 euro
3. PREMIUM - 150 contatti + Guida Resell - 15.99 euro
4. ULTIMATE - 1000+ contatti + Guida Resell - 19.99 euro

LISTINO PREZZI MEDI DAI FORNITORI:
- Scarpe: 30-80 euro
- Maglie: 6-10 euro
- Maglie da calcio: 10-15 euro
- Giubbotti: 30-50 euro
- Pantaloni: 10-20 euro
- Felpe: 10-15 euro
- Accessori: 10-30 euro

COME FUNZIONA:
1. Il cliente sceglie il pacchetto sul sito
2. Paga con carta, PayPal, Apple Pay, Google Pay
3. Riceve ISTANTANEAMENTE il PDF via email
4. Apre il PDF e trova tutti i link ai fornitori
5. Contatta i fornitori e ordina quello che vuole

FAQ COMUNI:
- E' affidabile? Si, abbiamo oltre 200 recensioni reali verificabili su TikTok
- Posso vedere le recensioni? Si, guarda i commenti sotto i nostri video TikTok @snazzylines
- C'e un minimo d'ordine? Dipende dal fornitore, la maggior parte non ha minimo
- Come ricevo il pacchetto? Via email, istantaneamente dopo il pagamento
- Posso avere un rimborso? I prodotti digitali non sono rimborsabili, ma se hai problemi scrivici
- Che brand ci sono? Nike, Adidas, Ralph Lauren, The North Face, Stone Island, Moncler, Burberry, Lacoste e molti altri
- Vendete roba falsa/replica? NO. I nostri fornitori vendono prodotti autentici a prezzi all'ingrosso, vintage e stock

LINK UTILI:
- Sito: snazzylines.store
- TikTok: @snazzylines
- Telegram: @snazzylines

REGOLE IMPORTANTI:
1. Non inventare MAI informazioni che non hai
2. Se non sai rispondere a qualcosa di specifico, di: Per questa domanda ti consiglio di scrivere direttamente a @snazzylines su Telegram, ti risponderanno il prima possibile!
3. Non discutere mai di rimborsi in dettaglio, rimanda sempre a @snazzylines
4. Non fare promesse di guadagno
5. Non usare parole come replica, 1:1, contraffatto
6. Dai risposte complete ma non esagerate, usa emoji per rendere tutto piu leggibile
7. Se qualcuno chiede il link diretto al sito, mandalo a snazzylines.store
8. Se qualcuno e scortese o aggressivo, resta gentile e professionale
9. Se qualcuno chiede cose non relative a SnazzyLines, rispondi brevemente e riporta la conversazione sul servizio"""

conversations = {}

def ask_groq(user_id, message):
    if user_id not in conversations:
        conversations[user_id] = []
    conversations[user_id].append({"role": "user", "content": message})
    if len(conversations[user_id]) > 20:
        conversations[user_id] = conversations[user_id][-20:]
    messages = [{"role": "system", "content": SYSTEM}] + conversations[user_id]
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 500, "temperature": 0.7}
    )
    result = r.json()
    try:
        reply = result["choices"][0]["message"]["content"]
        conversations[user_id].append({"role": "assistant", "content": reply})
        return reply
    except:
        return "DEBUG: " + json.dumps(result)[:500]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ciao! 👋 Sono l'assistente di SnazzyLines.\n\nPosso aiutarti con:\n🛍️ Info sui pacchetti e prezzi\n📦 Come funziona il servizio\n💰 Prezzi medi dai fornitori\n❓ Qualsiasi domanda su SnazzyLines\n\nScrivimi pure, sono qui per te! 🔥")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        risposta = ask_groq(update.effective_user.id, update.message.text)
        await update.message.reply_text(risposta)
    except Exception as e:
        await update.message.reply_text(f"DEBUG: {str(e)}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversations.pop(user_id, None)
    await update.message.reply_text("Conversazione resettata! Scrivimi pure 😊")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
