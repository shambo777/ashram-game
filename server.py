import asyncio
import os
import sqlite3
import logging
from flask import Flask, make_response, send_from_directory, request, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

# Включаем логирование ошибок
logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = "https://ashram-game.onrender.com"

bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher()
app = Flask(__name__)

# БАЗА ДАННЫХ В ПАМЯТИ
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

def db_update_player(user_id, race=None, prana=None, room_lvl=None):
    cursor = CONN.cursor()
    if race is not None: cursor.execute("UPDATE players SET race = ? WHERE user_id = ?", (race, user_id))
    if prana is not None: cursor.execute("UPDATE players SET prana = ? WHERE user_id = ?", (prana, user_id))
    if room_lvl is not None: cursor.execute("UPDATE players SET room_lvl = ? WHERE user_id = ?", (room_lvl, user_id))
    CONN.commit()

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

@app.route("/save_race", methods=["POST"])
def save_race():
    data = request.json
    db_update_player(int(data["user_id"]), race=data["race"])
    return jsonify({"status": "success"})

@app.route("/upgrade_room", methods=["POST"])
def upgrade_room():
    data = request.json
    user_id = int(data["user_id"])
    p = db_get_player(user_id)
    if p["prana"] >= 50:
        new_prana = p["prana"] - 50
        new_lvl = p["room_lvl"] + 1
        db_update_player(user_id, prana=new_prana, room_lvl=new_lvl)
        return jsonify({"prana": new_prana, "room_lvl": new_lvl})
    return jsonify({"error": "No prana"}), 400

# ЭТОТ МАРШРУТ ПРИНИМАЕТ ЗАПРОСЫ ОТ СЕРВЕРОВ TELEGRAM И МГНОВЕННО БУДИТ RENDER
@app.route("/webhook", methods=["POST"])
def webhook_handler():
    if bot:
        # Передаем входящий пакет данных напрямую в aiogram
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
        f"Ваш текущий баланс: {p['prana']} Праны.\n\n"
        "Нажмите на кнопку ниже, чтобы запустить Mini App:",
        reply_markup=kb
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    if bot:
        # Автоматическая привязка вебхука при старте сервера
        try:
            asyncio.run(bot.set_webhook(url=f"{RENDER_URL}/webhook", drop_pending_updates=True))
            logging.info("Сетевой мост Webhook успешно активирован в Telegram!")
        except Exception as e:
            logging.error(f"Ошибка активации Webhook: {e}")
            
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
