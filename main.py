import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = "8880773226:AAFl87uclfAXUQ1SBpOEUYsE3GAZy1PSCrg"
ADMIN_ID = 6899234650
CHANNEL_USERNAME = "cinematimehub"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("movies_final.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    name TEXT,
    file_id TEXT
)""")
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS hashtags (tag TEXT PRIMARY KEY)")
conn.commit()

cursor.execute("SELECT COUNT(*) FROM hashtags")
if cursor.fetchone() == 0:
    default_tags = ["#kino", "#yangikino", "#rek", "#fyp", "#عربي", "#افلام", "#مشاهدة", "#اكسبلور"]
    cursor.executemany("INSERT INTO hashtags VALUES (?)", [(tag,) for tag in default_tags])
    conn.commit()

class BotStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_name = State()
    waiting_for_video = State()
    waiting_for_delete_movie = State()
    waiting_for_add_tag = State()
    waiting_for_delete_tag = State()

async def check_subscription(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except Exception:
        return False

def get_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Kino qo'shish", callback_data="add_movie")
    builder.button(text="🗑 Kino o'chirish", callback_data="delete_movie")
    builder.button(text="#️⃣ Hashtag qo'shish", callback_data="add_tag")
    builder.button(text="❌ Hashtag o'chirish", callback_data="delete_tag")
    builder.button(text="📊 Statistika", callback_data="view_stats")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def get_sub_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🍿 Kanalga a'zo bo'lish", url=f"https://t.me{CHANNEL_USERNAME}")
    builder.button(text="✅ Tekshirish", callback_data="check_sub")
    builder.adjust(1)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    conn.commit()
    is_sub = await check_subscription(user_id)
    if not is_sub:
        await message.answer(f"❌ Botdan foydalanish uchun rasmiy kanalimizga a'zo bo'lishingiz shart:\n👉 @{CHANNEL_USERNAME}", reply_markup=get_sub_keyboard())
        return
    welcome_text = "👋 Salom! Kinolar olamiga xush kelibsiz.\n\n🎬 Kinoni topish uchun uning **kodini** yoki **nomini** yozib yuboring."
    if user_id == ADMIN_ID:
        await message.answer(welcome_text + "\n\n⚙️ Admin boshqaruv paneli:", reply_markup=get_admin_keyboard())
    else:
        await message.answer(welcome_text)

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: types.CallbackQuery):
    is_sub = await check_subscription(callback.from_user.id)
    if is_sub:
        await callback.message.delete()
        await callback.message.answer("🎉 Rahmat! Obuna tasdiqlandi. Kino kodini yoki nomini yuborishingiz mumkin.")
    else:
        await callback.answer("❌ Siz hali kanalga a'zo bo'lmagansiz!", show_alert=True)

@dp.callback_query(F.data == "view_stats")
async def view_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM movies")
    total_movies = cursor.fetchone()
    await callback.message.answer(f"📊 **Bot statistikasi:**\n\n👥 Foydalanuvchilar: {total_users} ta\n🎬 Yuklangan kinolar: {total_movies} ta")
    await callback.answer()

@dp.callback_query(F.data == "add_movie")
async def add_movie_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("1️⃣ Kinoga yangi **kod** bering:")
    await state.set_state(BotStates.waiting_for_code)
    await callback.answer()

@dp.message(BotStates.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text.strip())
    await message.answer("2️⃣ Endi kinoning **nomini** kiriting:")
    await state.set_state(BotStates.waiting_for_name)

@dp.message(BotStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip().lower())
    await message.answer("3️⃣ Endi kinoning **videosini** yuboring:")
    await state.set_state(BotStates.waiting_for_video)

@dp.message(BotStates.waiting_for_video, F.video | F.document)
async def process_video(message: types.Message, state: FSMContext):
    file_id = message.video.file_id if message.video else message.document.file_id
    data = await state.get_data()
    try:
        cursor.execute("INSERT INTO movies VALUES (?, ?, ?)", (data['code'], data['name'], file_id))
        conn.commit()
        await message.answer(f"✅ Kino muvaffaqiyatli saqlandi!\n🔑 Kod: `{data['code']}`\n📌 Nomi: {data['name']}", parse_mode="Markdown")
    except sqlite3.IntegrityError:
        await message.answer("❌ Bu kod bazada allaqachon mavjud!")
    await state.clear()

@dp.callback_query(F.data == "delete_movie")
async def delete_movie_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("🗑 O'chirmoqchi bo'lgan kinongizning **kodini** yuboring:")
    await state.set_state(BotStates.waiting_for_delete_movie)
    await callback.answer()

@dp.message(BotStates.waiting_for_delete_movie)
async def process_delete_movie(message: types.Message, state: FSMContext):
    code = message.text.strip()
    cursor.execute("SELECT * FROM movies WHERE code=?", (code,))
    if cursor.fetchone():
        cursor.execute("DELETE FROM movies WHERE code=?", (code,))
        conn.commit()
        await message.answer(f"🗑 Kodi `{code}` bo'lgan kino o'chirildi.")
    else:
        await message.answer("❌ Bunday kodli kino topilmadi.")
    await state.clear()

@dp.callback_query(F.data == "add_tag")
async def add_tag_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("#️⃣ Qo'shmoqchi bo'lgan hashtagni yozing:")
    await state.set_state(BotStates.waiting_for_add_tag)
    await callback.answer()

@dp.message(BotStates.waiting_for_add_tag)
async def process_add_tag(message: types.Message, state: FSMContext):
    tag = message.text.strip()
    if not tag.startswith("#"): tag = "#" + tag
    try:
        cursor.execute("INSERT INTO hashtags VALUES (?)", (tag,))
        conn.commit()
        await message.answer(f"✅ `{tag}` hashtagi qo'shildi.")
    except sqlite3.IntegrityError:
        await message.answer("❌ Bu hashtag allaqachon bor.")
    await state.clear()

@dp.callback_query(F.data == "delete_tag")
async def delete_tag_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    cursor.execute("SELECT tag FROM hashtags")
    tags = [row for row in cursor.fetchall()]
    await callback.message.answer(f"📋 Hozirgi hashtaglar: {', '.join(tags)}\n\n🗑 O'chirmoqchi bo'lgan hashtagni aniq yozing:")
    await state.set_state(BotStates.waiting_for_delete_tag)
    await callback.answer()

@dp.message(BotStates.waiting_for_delete_tag)
async def process_delete_tag(message: types.Message, state: FSMContext):
    tag = message.text.strip()
    cursor.execute("SELECT * FROM hashtags WHERE tag=?", (tag,))
    if cursor.fetchone():
        cursor.execute("DELETE FROM hashtags WHERE tag=?", (tag,))
        conn.commit()
        await message.answer(f"🗑 `{tag}` hashtagi bazadan o'chirildi.")
    else:
        await message.answer("❌ Bunday hashtag topilmadi.")
    await state.clear()

@dp.message()
async def search_movie(message: types.Message):
    user_id = message.from_user.id
    is_sub = await check_subscription(user_id)
    if not is_sub:
        await message.answer(f"❌ Botdan foydalanish uchun kanalga a'zo bo'ling: @{CHANNEL_USERNAME}", reply_markup=get_sub_keyboard())
        return
    query = message.text.strip()
    cursor.execute("SELECT * FROM movies WHERE code=?", (query,))
    movie = cursor.fetchone()
    if not movie:
        cursor.execute("SELECT * FROM movies WHERE name LIKE ?", (f"%{query.lower()}%",))
        movie = cursor.fetchone()
    if movie:
        code, name, file_id = movie
        cursor.execute("SELECT tag FROM hashtags")
        tags_list = [row[0] for row in cursor.fetchall()]
        current_hashtags = " ".join(tags_list)
        caption_text = f"🎬 **Kino nomi:** {name.title()}\n🔑 **Kodi:** {code}\n\n✨ {current_hashtags}"
        await message.answer_video(video=file_id, caption=caption_text, parse_mode="Markdown")
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text="🍿 Kino kodlari kanali", url=f"https://t.me{CHANNEL_USERNAME}")
        await message.answer("❌ Afsuski, bu kod yoki nom bo'yicha kino topilmadi.\nTo'g'ri kodlarni olish uchun kanalimizga o'ting:", reply_markup=builder.as_markup())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
