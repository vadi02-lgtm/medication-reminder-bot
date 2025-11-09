from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🐱 Medication Bot is starting..."

@app.route('/health')
def health():
    return "✅ OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("🚀 Fast Flask starting...")
    app.run(host='0.0.0.0', port=port, debug=False)
