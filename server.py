import asyncio
import os
import sqlite3
from flask import Flask, render_template_string, make_response, send_from_directory, request, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from threading import Thread

TOKEN = "8858569814:AAEGD4sMWYmVEur5jREoDq5UGGX8bsMcLU0"
NGROK_URL = "https://ashram-game.onrender.com"

bot = Bot(token=8858569814:AAEGD4sMWYmVEur5jREoDq5UGGX8bsMcLU0)
dp = Dispatcher()
app = Flask(__name__)

# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
def init_db():
    conn = sqlite3.connect("ashram_game.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            race TEXT DEFAULT 'Не выбрана',
            prana INTEGER DEFAULT 100,
            room_lvl INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

init_db()

def db_get_player(user_id):
    conn = sqlite3.connect("ashram_game.db")
    cursor = conn.cursor()
    cursor.execute("SELECT race, prana, room_lvl FROM players WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO players (user_id) VALUES (?)", (user_id,))
        conn.commit()
        row = ('Не выбрана', 100, 1)
    conn.close()
    return {"race": row[0], "prana": row[1], "room_lvl": row[2]}

def db_update_player(user_id, race=None, prana=None, room_lvl=None):
    conn = sqlite3.connect("ashram_game.db")
    cursor = conn.cursor()
    if race is not None: cursor.execute("UPDATE players SET race = ? WHERE user_id = ?", (race, user_id))
    if prana is not None: cursor.execute("UPDATE players SET prana = ? WHERE user_id = ?", (prana, user_id))
    if room_lvl is not None: cursor.execute("UPDATE players SET room_lvl = ? WHERE user_id = ?", (room_lvl, user_id))
    conn.commit()
    conn.close()

# ВЕБ-МАРШРУТЫ FLASK
with open("index.html", "r", encoding="utf-8") as f:
    html_layout = f.read()

@app.route('/<path:filename>')
def serve_static(filename):
    if filename.endswith(('.jpg', '.jpeg', '.png', '.webp')):
        return send_from_directory(os.getcwd(), filename)
    return "Файл не найден", 404

@app.route("/")
def home():
    response = make_response(render_template_string(html_layout))
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
    p = db_get_player(int(data["user_id"]))
    if p["prana"] >= 50:
        new_prana = p["prana"] - 50
        new_lvl = p["room_lvl"] + 1
        db_update_player(int(data["user_id"]), prana=new_prana, room_lvl=new_lvl)
        return jsonify({"prana": new_prana, "room_lvl": new_lvl})
    return jsonify({"error": "No prana"}), 400

# МАСШТАБНАЯ МНОГОУРОВНЕВАЯ СИСТЕМА КВЕСТОВ
MULTILEVEL_QUESTS = {
    "djinn_1": {
        "text": "🔮 ДЕЖУРСТВО С МУСТАФОЙ (Уровень 1): Иллюзии Маха-Майи\n\nВы патрулируете чердак заброшенного НИИ. Мустафа выпускает кольцо дыма из Кальяна Сатьи:\n«Астральные паразиты утверждают, что наша Бху-мандала — плоский диск. Давай разобьем морок Шримад Бхагаватам. Назови космическую ось, пронизывающую все планетные системы Вселенной?»",
        "buttons": [["Гора Меру (Сумеру)", "ans_right_djinn_2"], ["Древо Иггдрасиль", "ans_wrong"], ["Змей Шеша-нага", "ans_wrong"]]
    },
    "djinn_2": {
        "text": "🔮 ДЕЖУРСТВО С МУСТАФОЙ (Уровень 2): Дым Пуран\n\nПространство очищается, но Лярва Алкоголя пытается заключить с вами контр-контракт. Мустафа хитро улыбается:\n«Проверим её знание Шримад Бхагаватам. Какая аватара Господа Вишну приняла облик гигантского вепря, чтобы поднять Землю (Бхуми) со дна океана Гарбходака, куда её сбросил демон Хираньякша?»",
        "buttons": [["Матсья (Рыба)", "ans_wrong"], ["Вараха (Вепрь)", "ans_right_djinn_3"], ["Курма (Черепаха)", "ans_wrong"]]
    },
    "djinn_3": {
        "text": "🔮 ДЕЖУРСТВО С МУСТАФОЙ (Уровень 3): Контракт Времени\n\nЛярва вижжит. Мустафа достает древний свиток:\n«Финальный рубеж. Махабхарата гласит, что время в материальном мире циклично. Какова общая продолжительность всех четырех Юг (Сатья, Трета, Двапара и Кали), составляющих вместе одну Маха-югу в исчислении лет смертных?»",
        "buttons": [["4 320 000 лет", "ans_right_final"], ["1 200 000 лет", "ans_wrong"], ["100 000 000 лет", "ans_wrong"]]
    },
    "mag_1": {
        "text": "🧠 ДЕЖУРСТВО С АФАНАСИЕМ (Уровень 1): Матрица Координации\n\nАфанасий направляет советскую отвертку на разрыв ЛЭП УМПО. Его три головы произносят в унисон:\n«Для стабилизации гравитационного луча нужен нумерологический код. Из скольких глав состоит Бхагавад-Гита, поведанная Кришной Арджуне на поле Курукшетра?»",
        "buttons": [["12 глав", "ans_wrong"], ["18 глав", "ans_right_mag_2"], ["108 глав", "ans_wrong"]]
    },
    "mag_2": {
        "text": "🧠 ДЕЖУРСТВО С АФАНАСИЕМ (Уровень 2): Гравитация Древних\n\nДроны-черепа фиксируют новые астральные вспышки. Левая голова Афанасия (Память) кричит:\n«Вспомни Махабхарату! Кто был отцом пяти Пандавов (Юдхиштхиры, Бхимы, Арджуны, Накулы и Сахадевы) согласно земной родословной, чье проклятие заставило его уйти в леса?»",
        "buttons": [["Царь Панду", "ans_right_mag_3"], ["Царь Дхритараштра", "ans_wrong"], ["Мудрец Вьясадева", "ans_wrong"]]
    },
    "mag_3": {
        "text": "🧠 ДЕЖУРСТВО С АФАНАСИЕМ (Уровень 3): Код Создателя\n\nРазрыв ЛЭП почти затянут, гравитация колеблется. Афанасий требует высший ответ:\n«Ведическая космология описывает Творца нашей Вселенной — Брахму. Но у него есть предел жизни. Сколько длится один день Брахмы (Калпа) в Тонком Плане, равный одной дневной манифестации творения?»",
        "buttons": [["1000 Маха-юг (4.32 млрд лет)", "ans_right_final"], ["100 Маха-юг", "ans_wrong"], ["1 миллион лет", "ans_wrong"]]
    },
    "nag_1": {
        "text": "🐍 ДЕЖУРСТВО С ГАВРИИЛОМ (Уровень 1): Спираль Памяти\n\nИзумруд на посохе Гавриила закручивает реальность в Спираль Фибоначчи. Вокруг шипит смог Кали-Юги:\n«Чтобы пройти сквозь кольца времени, ответь на вопрос из Шива Пураны. Махадев Шива выпил страшный яд Халахала ради спасения мира от уничтожения во время пахтания океана. Какую память об этом хранит Его тело?»",
        "buttons": [["Его стопы стали золотыми", "ans_wrong"], ["Его горло стало синим (Нилакантха)", "ans_right_nag_2"], ["Открылся четвертый глаз", "ans_wrong"]]
    },
    "nag_2": {
        "text": "🐍 ДЕЖУРСТВО С ГАВРИИЛОМ (Уровень 2): Хроники Змей\n\nЗмеи на плечах Гавриила расправляют капюшоны. Из Хроник Акаши материализуется дух змеиного царя:\n«Кто из великих змеев (Нагов) ведической космологии служит вечным ложем для Господа Вишну в Причинном океане и держит на своих бесчисленных головах все планеты материального мира?»",
        "buttons": [["Васуки", "ans_wrong"], ["Такшака", "ans_wrong"], ["Ананта-Шеша", "ans_right_nag_3"]]
    },
    "nag_3": {
        "text": "🐍 ДЕЖУРСТВО С ГАВРИИЛОМ (Уровень 3): Алтарь Шивы\n\nМногоножки Забвения рассеиваются. Гавриил подводит вас к тонкоматериальному Алтарю:\n«Финальный вопрос Шива Пураны. Назовите священную ночь, когда преданные бодрствуют и медитируют на трансцендентный танец Господа Шивы (Тандава), разрушающий невежество?»",
        "buttons": [["Махашиваратри", "ans_right_final"], ["Дивали", "ans_wrong"], ["Холи", "ans_wrong"]]
    },
    "leviafan_1": {
        "text": "🔥 ДЕЖУРСТВО С ДЫКОМ (Уровень 1): Абсолютный Контроль\n\nДык воет на луну, его крио-доспехи гудят, защищая души Николая и Весемира:\n«Разум должен быть холодным, как Абсолютный Ноль! Ответь на вопрос из Вишну Пураны. Назови великого преданного мальчика, которого Нараяна защищал от всех смертельных казней его собственного отца Хираньякашипу?»",
        "buttons": [["Махараджа Прахлада", "ans_right_leviafan_2"], ["Царевич Дхрува", "ans_wrong"], ["Принц Бхишма", "ans_wrong"]]
    },
    "leviafan_2": {
        "text": "🔥 ДЕЖУРСТВО С ДЫКОМ (Уровень 2): Огненная Опора\n\nДык бьет трезубцем фазового сдвига, замораживая стаю Лярв. Но из тени УМПО выходит яростный демон:\n«Вишну Пурана и Шримад Бхагаватам описывают, что для спасения Прахлады Всевышний явился в ужасающей, невиданной ранее форме Получеловека-Полульва. Как зовут эту аватару?»",
        "buttons": [["Ваманадева", "ans_wrong"], ["Нрисимхадева", "ans_right_leviafan_3"], ["Парашурама", "ans_wrong"]]
    },
    "leviafan_3": {
        "text": "🔥 ДЕЖУРСТВО С ДЫКОМ (Уровень 3): Океан Абсолюта\n\nПромзона Уфы затихает, окутанная чистой энергией. Дык ухмыляется своей безумной улыбкой:\n«И последнее. Ведическая космология говорит, что наша Вселенная плавает в безбрежном океане материи, подобно пузырьку. Как называется этот первичный материальный океан, где возлежит Маха-Вишну, выдыхающий мириады вселенных?»",
        "buttons": [["Причинный океан (Каранаводака)", "ans_right_final"], ["Молочный океан", "ans_wrong"], ["Соленый океан", "ans_wrong"]]
    }
}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    p = db_get_player(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏰 Войти в Ашрам (База)", web_app=WebAppInfo(url=NGROK_URL))],
        [InlineKeyboardButton(text="⚔️ Начать дежурство (Квесты)", callback_data="start_duty")]
    ])
    await message.answer(
        f"Приветствую, {message.from_user.first_name}!\n\nСистема 'Bholenath Sanga' активна.\n"
        f"Ваш текущий баланс: {p['prana']} Праны. Уровень кельи: {p['room_lvl']}.\n\nВыберите действие:",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data == "start_duty")
async def start_duty_menu(callback: types.CallbackQuery):kb = InlineKeyboardMarkup(inline_keyboard=[(InlineKeyboardButton(text="🔮 Джинн Мустафа", callback_data="runquest_djinn_1")),(InlineKeyboardButton(text="🧠 Маг Афанасий", callback_data="runquest_mag_1")),(InlineKeyboardButton(text="🐍 Наг Гавриил", callback_data="runquest_nag_1")),(InlineKeyboardButton(text="🔥 Левиафан Дык", callback_data="runquest_leviafan_1"))])await callback.message.edit_text("С кем из хранителей Системы вы разделите ночное дежурство?", reply_markup=kb)@dp.callback_query(lambda c: c.data.startswith("runquest_"))async def handle_quests(callback: types.CallbackQuery):quest_key = callback.data.replace("runquest_", "")quest_data = MULTILEVEL_QUESTS.get(quest_key)if quest_data:kb = InlineKeyboardMarkup(inline_keyboard=[(InlineKeyboardButton(text=t, callback_data=f"ans_{c}")) for t, c in quest_data("buttons"))await callback.message.edit_text(quest_data("text"), reply_markup=kb)@dp.callback_query(lambda c: c.data.startswith("ans_"))async def handle_answers(callback: types.CallbackQuery):user_id = callback.from_user.idaction = callback.data.replace("ans_", "")if action == "wrong":kb = InlineKeyboardMarkup(inline_keyboard=[(InlineKeyboardButton(text="Попробовать снова", callback_data="start_duty")))await callback.message.edit_text("❌ ИСКАЖЕНИЕ СИСТЕМЫ...\n\nОтвет неверен. Ум поддался иллюзиям Кали-Юги. Настройте Координацию и попробуйте дежурство заново!", reply_markup=kb)elif action.startswith("right_") and (action.endswith("2") or action.endswith("3")):next_step = action.replace("right", "")kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Продолжить дежурство ➡️", callback_data=f"runquest{next_step}")]])await callback.message.edit_text("✨ ИСТИНА ОТКРЫТА! Вы успешно запечатали текущий сектор подпространства. Но паразиты наступают дальше...", reply_markup=kb)elif action == "right_final":p = db_get_player(user_id)new_prana = p("prana") + 300db_update_player(user_id, prana=new_prana)kb = InlineKeyboardMarkup(inline_keyboard=[(InlineKeyboardButton(text="В штаб Ашрама 🏰", callback_data="back_main")))await callback.message.edit_text(f"🎉 ПОЛНАЯ ПОБЕДА НАД ПОДПЛАНАМИ!\n\nВы полностью очистили сектор ЛЭП, проявив глубочайшие ведические знания. Система BSS стабилизирована.\n\nНаграда: +300 Праны!\nБаланс: {new_prana} Праны.", reply_markup=kb)@dp.callback_query(lambda c: c.data == "back_main")async def back_to_main(callback: types.CallbackQuery):p = db_get_player(callback.from_user.id)kb = InlineKeyboardMarkup(inline_keyboard=[(InlineKeyboardButton(text="🏰 Войти в Ашрам (База)", web_app=WebAppInfo(url=NGROK_URL))),(InlineKeyboardButton(text="⚔️ Начать дежурство (Квесты)", callback_data="start_duty"))])await callback.message.edit_text(f"Система 'Bholenath Sanga' активна.\nВаш баланс: {p('prana')} Праны.", reply_markup=kb)
