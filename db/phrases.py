import sqlite3
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import DB_PATH

router = Router()
logger = logging.getLogger(__name__)


# === FSM для очікування username
class SupportStates(StatesGroup):
    waiting_for_username = State()


# 🔁 Отримання випадкової фрази підтримки
def get_random_supportive_phrase():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM supportive_phrases_unique')
        count = cursor.fetchone()[0]

        if count == 0:
            logger.info("📥 Додаємо фрази підтримки в базу")
            phrases = [
                ("phrase1", "Ти сильніший, ніж думаєш! 🐱"),
                ("phrase2", "Кожен день — це новий шанс! 🐱"),
                ("phrase3", "Ти чудово справляєшся! 🐱"),
                ("phrase4", "Пам'ятай, ти не один! 🐱"),
                ("phrase5", "Твої почуття важливі і дійсні! 🐱"),
                ("phrase6", "Маленькі кроки ведуть до великих змін! 🐱"),
                ("phrase7", "Бути людиною — означає мати різні емоції, і це нормально. 🐱"),
                ("phrase8", "Ти можеш впоратися з цим днем! 🐱"),
                ("phrase9", "Дозволь собі відпочити, коли це потрібно. 🐱"),
                ("phrase10", "Ти заслуговуєш на турботу і любов. 🐱")
            ]
            cursor.executemany(
                'INSERT OR IGNORE INTO supportive_phrases_unique (phrase_id, text) VALUES (?, ?)',
                phrases
            )
            conn.commit()

        cursor.execute('SELECT text FROM supportive_phrases_unique ORDER BY RANDOM() LIMIT 1')
        result = cursor.fetchone()
        conn.close()

        return result[0] if result else "Ти молодець! Все буде добре 🐱"
    except Exception as e:
        logger.error(f"❌ Помилка отримання фрази підтримки: {e}")
        return "Ти молодець! Все буде добре 🐱"


# === Обробник кнопки "Фраза підтримки"
@router.message(F.text == "🗯 Фраза підтримки")
async def supportive_phrase_handler(message: Message):
    phrase = get_random_supportive_phrase()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Інша фраза", callback_data="another_phrase")],
        [InlineKeyboardButton(text="🤝 Надіслати другу", callback_data="send_phrase")]
    ])

    await message.answer(
        f"🐱 Ось фраза підтримки спеціально для тебе:\n\n{phrase}",
        reply_markup=keyboard
    )


# === Інша фраза (callback)
@router.callback_query(F.data == "another_phrase")
async def another_phrase_handler(callback: CallbackQuery):
    phrase = get_random_supportive_phrase()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Інша фраза", callback_data="another_phrase")],
        [InlineKeyboardButton(text="🤝 Надіслати другу", callback_data="send_phrase")]
    ])

    await callback.message.edit_text(
        f"🐱 Ось ще одна фраза підтримки для тебе:\n\n{phrase}",
        reply_markup=keyboard
    )
    await callback.answer()


# === Кнопка "Надіслати другу"
@router.callback_query(F.data == "send_phrase")
async def request_username(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🐱 Введіть @username друга, якому хочете надіслати фразу підтримки анонімно:")
    await state.set_state(SupportStates.waiting_for_username)
    await callback.answer()


# === Обробка введення @username
@router.message(F.text.startswith("@"))
async def process_username(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != SupportStates.waiting_for_username.state:
        return

    username = message.text.strip().replace("@", "")
    phrase = get_random_supportive_phrase()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT telegram_id FROM users WHERE username = ?', (username,))
        recipient = cursor.fetchone()
        conn.close()

        if recipient:
            await message.bot.send_message(
                chat_id=recipient[0],
                text=f"🐱 Хтось надіслав тобі котика підтримки:\n\n{phrase}\n\nВін дуже хоче, щоб ти посміхнувся(-лась) сьогодні!"
            )
            await message.answer(f"🐱 Фразу підтримки надіслано до @{username}!")
        else:
            await message.answer(f"🐱 На жаль, користувача @{username} не знайдено або він ще не взаємодіяв з ботом.")

    except Exception as e:
        logger.error(f"❌ Помилка надсилання фрази підтримки: {e}")
        await message.answer("🐱 Виникла помилка. Спробуйте пізніше.")

    await state.clear()


# === Реєстрація роутера
def register_supportive_handlers(dp):
    dp.include_router(router)
