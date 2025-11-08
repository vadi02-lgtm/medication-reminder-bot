from flask import Flask
import threading
import asyncio
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🐱 Medication Bot is running!"

@app.route('/health')
def health():
    return "✅ OK"

def run_bot():
    """Запускает бота в отдельном потоке"""
    from bot_reminder import MedicationReminderBot, get_token
    
    token = get_token()
    if token:
        bot = MedicationReminderBot(token)
        asyncio.run(bot.run())

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask сервер
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)