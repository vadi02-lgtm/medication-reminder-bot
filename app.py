from flask import Flask
import threading
import os
import time
import asyncio
import subprocess
import sys

app = Flask(__name__)

@app.route('/')
def home():
    return "🐱 Medication Bot is running! Bot is starting in background..."

@app.route('/health')
def health():
    return "✅ OK"

def run_bot():
    """Запускает бота в отдельном ПРОЦЕССЕ"""
    time.sleep(10)  # Даём время Flask полностью запуститься
    
    try:
        print("🤖 ЗАПУСКАЕМ TELEGRAM БОТА В ОТДЕЛЬНОМ ПРОЦЕССЕ...")
        
        # Запускаем бота в отдельном процессе
        process = subprocess.Popen([sys.executable, 'bot_reminder.py'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 text=True)
        
        print(f"✅ Бот запущен с PID: {process.pid}")
        
        # Мониторим вывод бота
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"🤖 БОТ: {output.strip()}")
        
        # Если процесс завершился
        rc = process.poll()
        print(f"❌ Бот завершился с кодом: {rc}")
        
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()

# Альтернативный простой способ - просто запустить бота
def simple_bot_start():
    """Простой запуск бота"""
    time.sleep(8)
    try:
        print("🚀 ПРОСТОЙ ЗАПУСК БОТА...")
        # Импортируем и запускаем бота напрямую
        from bot_reminder import MedicationReminderBot, get_token
        
        token = get_token()
        if token:
            print("✅ Токен найден, создаем бота...")
            bot = MedicationReminderBot(token)
            print("✅ Бот создан, запускаем...")
            
            # Запускаем в этом же потоке
            import asyncio
            asyncio.run(bot.run())
        else:
            print("❌ ТОКЕН НЕ НАЙДЕН! Проверьте переменную BOT_TOKEN")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

# Запускаем бота
print("🚀 Инициализируем запуск бота...")
bot_thread = threading.Thread(target=simple_bot_start, daemon=True)
bot_thread.start()
print("✅ Фоновый поток бота запущен")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Запускаем Flask сервер на порту {port}...")
    print("📱 Бот должен запуститься через 8 секунд...")
    app.run(host='0.0.0.0', port=port, debug=False)
