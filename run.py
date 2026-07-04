import sqlite3
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def run_health_server():
    server = HTTPServer(("0.0.0.0", 10000), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_health_server, daemon=True).start()

BOT_TOKEN = "8944975699:AAHBQ_Ad96Cv7hgziUWj8INen3kGHCUX9cg"
ADMIN_USER_ID = 5585731063
MAIN_CHANNEL = "cinematimehub"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

db_conn = sqlite3.connect("movies_final.db")
db_cursor = db_conn.cursor()
db_cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    name TEXT,
    file_id TEXT
)""")
db_cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
db_cursor.execute("CREATE TABLE IF NOT EXISTS hashtags (tag TEXT PRIMARY KEY)")
db_conn.commit()

db_cursor.execute("SELECT COUNT(*) FROM hashtags")
if db_cursor.fetchone() == 0:
    tags_data = [("#kino",), ("#yangikino",), ("#rek",), ("#fyp",)]
    db_cursor.executemany("INSERT INTO hashtags VALUES (?)", tags_data)
    db_conn.commit()

class MyBotStates(StatesGroup):
    input_code = State()
    input_name = State()
    input_video = State()
    delete_movie_code = State()
    add_new_tag = State()
    delete_old_tag = State()

async def check_user_sub(user_id: int) -> bool:
    if user_id == ADMIN_USER_ID:
        return True
    try:
        chat_member = await bot.get_chat_member(chat_id=f"@{MAIN_CHANNEL}", user_id=user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except Exception:
        return False

def get_main_reply_keyboard(user_id: int):
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔍 Kino qidirish")
    if user_id == ADMIN_USER_ID:
        builder.button(text="⚙️ Admin Panel")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, is_persistent=True)

def make_admin_kb():
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="➕ Kino qo'shish", callback_data="add_movie")
    kb_builder.button(text="🗑 Kino o'chirish", callback_data="delete_movie")
    kb_builder.button(text="#️⃣ Hashtag qo'shish", callback_data="add_tag")
    kb_builder.button(text="❌ Hashtag o'chirish", callback_data="delete_tag")
    kb_builder.button(text="📊 Statistika", callback_data="view_stats")
    kb_builder.adjust(2, 2, 1)
    return kb_builder.as_markup()

def make_sub_kb():
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="🍿 Kanalga a'zo bo'lish", url=f"https://t.me{MAIN_CHANNEL}")
    kb_builder.button(text="✅ Tekshirish", callback_data="check_sub")
    kb_builder.adjust(1)
    return kb_builder.as_markup()

async def delete_message_after_delay(chat_id: int, message_id: int, delay: int = 5):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    uid = message.from_user.id
    db_cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (uid,))
    db_conn.commit()
    
    user_status = await check_user_sub(uid)
    if not user_status:
        await message.answer(f"❌ Botdan foydalanish uchun rasmiy kanalimizga a'zo bo'lishingiz shart:\n👉 @{MAIN_CHANNEL}", reply_markup=make_sub_kb())
        return
        
    txt = "👋 Salom! Kinolar olamiga xush kelibsiz.\n\n🎬 Kinoni topish uchun uning kodini yoki nomini to'g'ridan-to'g'ri yozib yuboring."
    sent_msg = await message.answer(txt, reply_markup=get_main_reply_keyboard(uid))
    
    asyncio.create_task(delete_message_after_delay(message.chat.id, sent_msg.message_id, 15))
    asyncio.create_task(delete_message_after_delay(message.chat.id, message.message_id, 15))

@dp.message(F.text == "🔍 Kino qidirish")
async def search_btn_click(message: types.Message):
    sent_msg = await message.answer("🎬 Kino topish uchun uning kodini yoki nomini yozib yuboring:")
    asyncio.create_task(delete_message_after_delay(message.chat.id, message.message_id, 10))
    asyncio.create_task(delete_message_after_delay(message.chat.id, sent_msg.message_id, 10))

@dp.message(F.text == "⚙️ Admin Panel")
async def admin_panel_click(message: types.Message):
    if message.from_user.id != ADMIN_USER_ID: return
    await message.answer("⚙️ Boshqaruv paneli:", reply_markup=make_admin_kb())
    asyncio.create_task(delete_message_after_delay(message.chat.id, message.message_id, 3))

@dp.callback_query(F.data == "check_sub")
async def check_sub_btn(callback: types.CallbackQuery):
    user_status = await check_user_sub(callback.from_user.id)
    if user_status:
        await callback.message.delete()
        sent_msg = await callback.message.answer("🎉 Rahmat! Obuna tasdiqlandi. Kino kodini yoki nomini yuborishingiz mumkin.", reply_markup=get_main_reply_keyboard(callback.from_user.id))
        asyncio.create_task(delete_message_after_delay(callback.message.chat.id, sent_msg.message_id, 10))
    else:
        await callback.answer("❌ Siz hali kanalga a'zo bo'lmagansiz!", show_alert=True)

@dp.callback_query(F.data == "view_stats")
async def view_stats_btn(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_USER_ID: return
    db_cursor.execute("SELECT COUNT(*) FROM users")
    u_count = db_cursor.fetchone()
    db_cursor.execute("SELECT COUNT(*) FROM movies")
    m_count = db_cursor.fetchone()
    await callback.message.answer(f"📊 Bot statistikasi:\n\n👥 Foydalanuvchilar: {u_count} ta\n🎬 Yuklangan kinolar: {m_count} ta")
    await callback.answer()

@dp.callback_query(F.data == "add_movie")
async def add_movie_btn(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_USER_ID: return
    await callback.message.answer("1️⃣ Kinoga yangi kod bering:")
    await state.set_state(MyBotStates.input_code)
    await callback.answer()

@dp.message(MyBotStates.input_code)
async def get_code_state(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text.strip())
    await message.answer("2️⃣ Endi kinoning nomini kiriting:")
    await state.set_state(MyBotStates.input_name)

@dp.message(MyBotStates.input_name)
async def get_name_state(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip().lower())
    await message.answer("3️⃣ Endi kinoning videosini yuboring:")
    await state.set_state(MyBotStates.input_video)

@dp.message(MyBotStates.input_video, F.video | F.document)
async def get_video_state(message: types.Message, state: FSMContext):
    f_id = message.video.file_id if message.video else message.document.file_id
    stored_data = await state.get_data()
    try:
        db_cursor.execute("INSERT INTO movies VALUES (?, ?, ?)", (stored_data['code'], stored_data['name'], f_id))
        db_conn.commit()
        await message.answer(f"✅ Kino muvaffaqiyatli saqlandi!\n🔑 Kod: {stored_data['code']}\n📌 Nomi: {stored_data['name']}")
    except sqlite3.IntegrityError:
        await message.answer("❌ Bu kod bazada allaqachon mavjud!")
    await state.clear()

@dp.callback_query(F.data == "delete_movie")
async def delete_movie_btn(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_USER_ID: return
    await callback.message.answer("🗑 O'chirmoqchi bo'lgan kinongizning kodini yuboring:")
    await state.set_state(MyBotStates.delete_movie_code)
    await callback.answer()

@dp.message(MyBotStates.delete_movie_code)
async def do_delete_movie(message: types.Message, state: FSMContext):
    m_code = message.text.strip()
    db_cursor.execute("SELECT * FROM movies WHERE code=?", (m_code,))
    if db_cursor.fetchone():
        db_cursor.execute("DELETE FROM movies WHERE code=?", (m_code,))
        db_conn.commit()
        await message.answer(f"🗑 Kodi {m_code} bo'lgan kino o'chirildi.")
    else:
        await message.answer("❌ Bunday kodli kino topilmadi.")
    await state.clear()

@dp.callback_query(F.data == "add_tag")
async def add_tag_btn(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_USER_ID: return
    await callback.message.answer("#️⃣ Qo'shmoqchi bo'lgan hashtagni yozing:")
    await state.set_state(MyBotStates.add_new_tag)
    await callback.answer()

@dp.message(MyBotStates.add_new_tag)
async def do_add_tag(message: types.Message, state: FSMContext):
    new_tag = message.text.strip()
    if not new_tag.startswith("#"): new_tag = "#" + new_tag
    try:
        db_cursor.execute("INSERT INTO hashtags VALUES (?)", (new_tag,))
        db_conn.commit()
        await message.answer(f"✅ {new_tag} hashtagi qo'shildi.")
    except sqlite3.IntegrityError:
        await message.answer("❌ Bu hashtag allaqachon bor.")
    await state.clear()

@dp.callback_query(F.data == "delete_tag")
async def delete_tag_btn(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_USER_ID: return
    db_cursor.execute("SELECT tag FROM hashtags")
    all_tags = [row for row in db_cursor.fetchall()]
    await callback.message.answer(f"📋 Hozirgi hashtaglar: {', '.join(all_tags)}\n\n🗑 O'chirmoqchi bo'lgan hashtagni aniq yozing:")
    await state.set_state(MyBotStates.delete_old_tag)
    await callback.answer()

@dp.message(MyBotStates.delete_old_tag)
async def do_delete_tag(message: types.Message, state: FSMContext):
    old_tag = message.text.strip()
db_cursor.execute("SELECT * FROM hashtags WHERE tag=?", (old_tag,))if db_cursor.fetchone():db_cursor.execute("DELETE FROM hashtags WHERE tag=?", (old_tag,))db_conn.commit()await message.answer(f"🗑 {old_tag} hashtagi bazadan o'chirildi.")else:await message.answer("❌ Bunday hashtag topilmadi.")await state.clear()@dp.message()async def main_message_handler(message: types.Message):uid = message.from_user.iduser_status = await check_user_sub(uid)if not user_status:await message.answer(f"❌ Botdan foydalanish uchun kanalga a'zo bo'ling: @{MAIN_CHANNEL}", reply_markup=make_sub_kb())returnif message.video and message.caption:caption_text = message.captionif "instagram.com" in caption_text or any(x in caption_text.lower() for x in ["insta", "reel", "video", "post"]):await message.answer(f"📋 Instagram videosidagi matn ajratib olindi:\n\n{caption_text}")returnsearch_query = message.text.strip() if message.text else ""if not search_query: returndb_cursor.execute("SELECT * FROM movies WHERE code=?", (search_query,))movie_data = db_cursor.fetchone()if not movie_data:db_cursor.execute("SELECT * FROM movies WHERE name LIKE ?", (f"%{search_query.lower()}%",))movie_data = db_cursor.fetchone()if movie_data:m_code, m_name, f_id = movie_datadb_cursor.execute("SELECT tag FROM hashtags")tags_res = [row for row in db_cursor.fetchall()]combined_tags = " ".join(tags_res)cap = f"🎬 Kino nomi: {m_name.title()}\n🔑 Kodi: {m_code}\n\n✨ {combined_tags}"await message.answer_video(video=f_id, caption=cap)asyncio.create_task(delete_message_after_delay(message.chat.id, message.message_id, 3))else:fail_msg = await message.answer("❌ Afsuski, bu kod yoki nom bo'yicha kino topilmadi. Iltimos, kodni to'g'ri kiriting.")asyncio.create_task(delete_message_after_delay(message.chat.id, message.message_id, 5))asyncio.create_task(delete_message_after_delay(message.chat.id, fail_msg.message_id, 5))async def main():await dp.start_polling(bot)if name == "main":asyncio.run(main())
