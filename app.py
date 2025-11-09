from flask import Flask
import threading
import os
import time
import asyncio

app = Flask(__name__)

@app.route('/')
def home():
    return "🐱 Medication Bot is running! Bot should be working in background."

@app.route('/health')
def health():
    return "✅ OK"

def run_bot():
    """Запускает бота в отдельном потоке"""
    time.sleep(5)  # Даём время Flask запуститься
    
    try:
        print("🤖 ЗАПУСКАЕМ TELEGRAM БОТА...")
        from bot_reminder import MedicationReminderBot, get_token
        
        token = get_token()
        if token:
            print(f"✅ Токен получен, запускаем бота...")
            bot = MedicationReminderBot(token)
            
            # Создаем новое событийное loop для этого потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot.run())
        else:
            print("❌ Токен бота не найден!")
            
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()

# Запускаем бота при старте приложения
print("🚀 Инициализируем запуск бота в фоне...")
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
print("✅ Бот запускается в фоновом потоке")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Запускаем Flask сервер на порту {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
