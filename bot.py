import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

# Konfiguratsiya: BU YERGA O'Z MA'LUMOTLARINGIZNI KIRITING
BOT_TOKEN = "8260330510:AAHLseb65AyJm5G8wO0YFvMP7O3HJ2Y-kls"  # @BotFather dan olingan token
ADMIN_IDS = [8292713568, 8292713568]      # O'zingizning va ikkinchi adminning Telegram ID raqami
CHANNEL_ID = -1002714951758                  # Kanal ID raqami (-100 bilan boshlanadi)
GROUP_ID = -1002669474162                    # Guruh ID raqami (-100 bilan boshlanadi)
CHANNEL_LINK = "https://t.me/portfolio_1213312_port"  # To'liq kanal linki
GROUP_LINK = "https://t.me/ARZUACADEMY"    # To'liq guruh linki

# Loggingni sozlash
logging.basicConfig(level=logging.INFO)

# FSM (Finite State Machine) holatlari
class AdminStates(StatesGroup):
    waiting_for_file = State()
    waiting_for_broadcast = State()

# Ma'lumotlar bazasi bilan ishlash
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    # Foydalanuvchilar jadvali
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        is_approved INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0
    )
    ''')
    # Fayl uchun jadval
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    # Boshlang'ich fayl ID sini kiritish (agar mavjud bo'lmasa)
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('file_id', 'None')")
    conn.commit()
    conn.close()

# Foydalanuvchi funksiyalari
def add_user(user_id, username):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_blocked = 0")
    users = cursor.fetchall()
    conn.close()
    return users

def update_user_approval(user_id, status):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_approved = ? WHERE user_id = ?", (status, user_id))
    conn.commit()
    conn.close()
    
def update_user_block(user_id, status):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (status, user_id))
    conn.commit()
    conn.close()

# Fayl funksiyalari
def update_file_id(file_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE config SET value = ? WHERE key = 'file_id'", (file_id,))
    conn.commit()
    conn.close()

def get_file_id():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = 'file_id'")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Bot va dispetcherni yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Majburiy obunani tekshirish funksiyasi
async def check_subscription(user_id: int):
    try:
        member_channel = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        member_group = await bot.get_chat_member(chat_id=GROUP_ID, user_id=user_id)
        if member_channel.status not in ['member', 'administrator', 'creator'] or \
           member_group.status not in ['member', 'administrator', 'creator']:
            return False
        return True
    except TelegramBadRequest:
        return False

# Tugmalarni yasash
def get_subscribe_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="👥 Guruhga qo'shilish", url=GROUP_LINK)],
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_subscription")]
    ])
    return keyboard

# /start buyrug'i uchun handler
@dp.message(Command("start"))
async def start_command(message: Message):
    user = message.from_user
    add_user(user.id, user.username or user.full_name)
    
    if await check_subscription(user.id):
        db_user = get_user(user.id)
        if db_user and db_user[3] == 1: # is_blocked
             await message.answer("Siz botdan foydalanish huquqidan mahrum qilingansiz (bloklangansiz).")
             return

        await message.answer(f"Assalomu alaykum, {user.full_name}!\n\nBotdan to'liq foydalanishingiz mumkin. Quyida siz uchun maxsus fayl.")
        if db_user and db_user[2] == 1: # is_approved
            file_id = get_file_id()
            if file_id and file_id != 'None':
                try:
                    await bot.send_document(chat_id=user.id, document=file_id, caption="Marhamat, siz uchun tayyorlangan fayl.")
                except TelegramBadRequest:
                    await message.answer("Admin tomonidan hali fayl yuklanmagan yoki fayl bilan bog'liq muammo yuzaga keldi.")
            else:
                await message.answer("Hozircha yuboriladigan fayl mavjud emas.")
        else:
            await message.answer("Faylni olish uchun admin tasdiqlashini kuting.")
            for admin_id in ADMIN_IDS:
                await bot.send_message(admin_id, f"Yangi foydalanuvchi: [{user.full_name}](tg://user?id={user.id}) fayl olish uchun ruxsat kutmoqda.", 
                                       parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                           [InlineKeyboardButton(text="✅ Ruxsat berish", callback_data=f"approve_{user.id}")],
                                           [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"decline_{user.id}")]
                                       ]))
    else:
        await message.answer(
            "Botdan to'liq foydalanish uchun, iltimos, quyidagi kanal va guruhga obuna bo'ling. Keyin 'Tasdiqlash' tugmasini bosing.",
            reply_markup=get_subscribe_keyboard()
        )

# "Tasdiqlash" tugmasi uchun handler
@dp.callback_query(F.data == "check_subscription")
async def handle_check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    
    if await check_subscription(user_id):
        await start_command(callback.message)
    else:
        await callback.message.answer(
            "Siz hali barcha kanallarga obuna bo'lmadingiz. Iltimos, obuna bo'lib, qayta urinib ko'ring.",
            reply_markup=get_subscribe_keyboard()
        )
    await callback.answer()

# ----------------- ADMIN QISMI -----------------

# Admin panelini ochuvchi buyruq
@dp.message(Command("admin"), F.from_user.id.in_(ADMIN_IDS))
async def admin_panel(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 Faylni O'zgartirish/Qo'shish", callback_data="change_file")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar Ro'yxati", callback_data="list_users")],
        [InlineKeyboardButton(text="📤 Ommaviy Xabar Yuborish", callback_data="broadcast")]
    ])
    await message.answer("Salom, admin! Kerakli bo'limni tanlang:", reply_markup=keyboard)

# Admin panel tugmalari uchun handler
@dp.callback_query(F.data.in_(['change_file', 'list_users', 'broadcast']), F.from_user.id.in_(ADMIN_IDS))
async def admin_callbacks(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    if callback.data == "change_file":
        await callback.message.answer("Yangi faylni (dokument) yuboring:")
        await state.set_state(AdminStates.waiting_for_file)
    elif callback.data == "list_users":
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, is_approved, is_blocked FROM users")
        users = cursor.fetchall()
        conn.close()

        if not users:
            await callback.message.answer("Hozircha foydalanuvchilar yo'q.")
            return

        text = "Foydalanuvchilar ro'yxati:\n\n"
        for user in users:
            user_id, username, approved, blocked = user
            status = []
            if approved: status.append("✅ Ruxsat berilgan")
            if blocked: status.append("🚫 Bloklangan")
            text += f"👤 [{username or user_id}](tg://user?id={user_id})\n   Holati: {', '.join(status) or 'Kutmoqda'}\n"
            text += f"   /block_{user_id}  /unblock_{user_id}\n\n"
        
        await callback.message.answer(text, parse_mode="Markdown")

    elif callback.data == "broadcast":
        await callback.message.answer("Barcha foydalanuvchilarga yuborish uchun xabarni (matn, rasm, video...) yuboring:")
        await state.set_state(AdminStates.waiting_for_broadcast)

    await callback.answer()

# Foydalanuvchini bloklash
@dp.message(lambda message: message.text and message.text.startswith('/block_'), F.from_user.id.in_(ADMIN_IDS))
async def block_user(message: Message):
    try:
        user_id = int(message.text.split('_')[1])
        update_user_block(user_id, 1)
        await message.answer(f"{user_id} raqamli foydalanuvchi bloklandi.")
    except (ValueError, IndexError):
        await message.answer("Noto'g'ri format. Misol: /block_12345678")

# Foydalanuvchini blokdan chiqarish
@dp.message(lambda message: message.text and message.text.startswith('/unblock_'), F.from_user.id.in_(ADMIN_IDS))
async def unblock_user(message: Message):
    try:
        user_id = int(message.text.split('_')[1])
        update_user_block(user_id, 0)
        await message.answer(f"{user_id} raqamli foydalanuvchi blokdan chiqarildi.")
    except (ValueError, IndexError):
        await message.answer("Noto'g'ri format. Misol: /unblock_12345678")


# Yangi faylni qabul qilish
@dp.message(StateFilter(AdminStates.waiting_for_file), F.document, F.from_user.id.in_(ADMIN_IDS))
async def file_received(message: Message, state: FSMContext):
    file_id = message.document.file_id
    update_file_id(file_id)
    await state.clear()
    await message.answer("✅ Fayl muvaffaqiyatli saqlandi va yangilandi!")

# Ommaviy xabarni qabul qilish va yuborish
@dp.message(StateFilter(AdminStates.waiting_for_broadcast), F.from_user.id.in_(ADMIN_IDS))
async def broadcast_received(message: Message, state: FSMContext):
    await state.clear()
    users = get_all_users()
    sent_count = 0
    failed_count = 0
    
    await message.answer(f"Xabar yuborish boshlandi. Jami foydalanuvchilar: {len(users)}")

    for user in users:
        user_id = user[0]
        try:
            await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logging.error(f"Xabar yuborishda xatolik {user_id}: {e}")
        await asyncio.sleep(0.1) # Telegram limitlariga tushmaslik uchun

    await message.answer(f"✅ Xabar yuborish yakunlandi.\n\nMuvaffaqiyatli: {sent_count}\nXatolik: {failed_count}")

# Foydalanuvchiga ruxsat berish/rad etish
@dp.callback_query(F.data.startswith(('approve_', 'decline_')), F.from_user.id.in_(ADMIN_IDS))
async def approve_decline_user(callback: CallbackQuery):
    action, user_id_str = callback.data.split('_')
    user_id = int(user_id_str)
    
    if action == 'approve':
        update_user_approval(user_id, 1)
        await callback.message.edit_text(f"✅ [{user_id}](tg://user?id={user_id}) ga faylni olish uchun ruxsat berildi.", parse_mode="Markdown")
        
        file_id = get_file_id()
        if file_id and file_id != 'None':
            try:
                await bot.send_document(user_id, file_id, caption="Sizga admin tomonidan faylni olishga ruxsat berildi. Marhamat!")
            except Exception as e:
                await callback.answer(f"Foydalanuvchiga fayl yuborib bo'lmadi: {e}", show_alert=True)
        else:
            await bot.send_message(user_id, "Sizga admin tomonidan ruxsat berildi, lekin hozircha yuboriladigan fayl mavjud emas.")
            
    elif action == 'decline':
        update_user_approval(user_id, 0)
        await callback.message.edit_text(f"❌ [{user_id}](tg://user?id={user_id}) ga fayl olish rad etildi.", parse_mode="Markdown")
        await bot.send_message(user_id, "Afsuski, admin so'rovingizni rad etdi.")
        
    await callback.answer()

# Asosiy funksiya
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
