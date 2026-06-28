import asyncio
import os
import sqlite3
import logging
from flask import Flask, make_response, send_from_directory, request, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

# Считываем настройки окружения Render
TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = "https://onrender.com"

bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher()
app = Flask(__name__)

CONN = sqlite3.connect(":memory:", check_same_thread=False)

def init_db():
    cursor = CONN.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            race TEXT DEFAULT 'Не выбрана',
            prana INTEGER DEFAULT 100,
            room_lvl INTEGER DEFAULT 1
        )
    """)
    CONN.commit()

init_db()

def db_get_player(user_id):
    cursor = CONN.cursor()
    cursor.execute("SELECT race, prana, room_lvl FROM players WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO players (user_id) VALUES (?)", (user_id,))
        CONN.commit()
        return {"race": "Не выбрана", "prana": 100, "room_lvl": 1}
    return {"race": str(row[0]), "prana": int(row[1]), "room_lvl": int(row[2])}

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

@app.route('/<path:filename>')
def serve_static(filename):
    if filename.endswith(('.jpg', '.jpeg', '.png', '.webp', '.html', '.js', '.css')):
        return send_from_directory(os.getcwd(), filename)
    return "Файл не найден", 404

@app.route("/")
def home():
    response = make_response(send_from_directory(os.getcwd(), "index.html"))
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

@app.route("/get_profile")
def get_profile():
    user_id = int(request.args.get("user_id", 999))
    return jsonify(db_get_player(user_id))

# ОБРАБОТЧИК ДЛЯ ВХОДЯЩИХ СИГНАЛОВ ОТ TELEGRAM (WEBHOOK)
@app.route("/webhook", methods=["POST"])
def webhook_handler():
    if bot:
        # Принимаем зашифрованный пакет от Telegram и передаем его в движок бота
        update = types.Update.model_validate(request.json, context={"bot": bot})
        asyncio.run(dp.feed_update(bot, update))
    return "OK", 200

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    p = db_get_player(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏰 Войти в Ашрам", web_app=WebAppInfo(url=RENDER_URL))]
    ])
    await message.answer(
        f"Приветствую! Система 'Bholenath Sanga' активна.\n"
        f"Ваш баланс: {p['prana']} Праны.\n\n"
        "Нажмите на кнопку ниже, чтобы запустить Mini App:",
        reply_markup=kb
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    if bot:
        # Принудительно заставляем Telegram слать все пакеты на адрес /webhook нашего сайта
        asyncio.run(bot.set_webhook(url=f"{RENDER_URL}/webhook"))
        print("Сетевой шлюз Webhook успешно развернут!")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
