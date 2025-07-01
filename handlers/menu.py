from aiogram import Router
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
import logging
from aiogram.filters import Command
from aiogram import F  # ← оце і є F
from aiogram.fsm.context import FSMContext



logger = logging.getLogger(__name__)
router = Router()

# 📌 Створення постійної клавіатури (persistent)
MAIN_MENU_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧪 Пройти тест"), KeyboardButton(text="❌ Скасувати")],
        [KeyboardButton(text="🗯 Фраза підтримки"), KeyboardButton(text="🤝 Поділитись з другом")],
        [KeyboardButton(text="🐾 Про проєкт"), KeyboardButton(text="💸 Задонатити")],
        [KeyboardButton(text="🤖 ШІ кіт Нейрон")]
    ],
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="Обери дію"
)

@router.message(F.text == "❌ Скасувати")
async def cancel_from_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🛑 Дію скасовано. Ти знову в головному меню.", reply_markup=MAIN_MENU_KEYBOARD)


# 📋 Показ головного меню (універсально — для Message і CallbackQuery)
async def show_main_menu(event, *_):
    try:
        if isinstance(event, CallbackQuery):
            await event.answer()
            await event.message.answer("🐱 Головне меню. Обери опцію:", reply_markup=MAIN_MENU_KEYBOARD)

        elif isinstance(event, Message):
            await event.answer("🐱 Головне меню. Обери опцію:", reply_markup=MAIN_MENU_KEYBOARD)

    except Exception as e:
        logger.error(f"❌ Помилка при показі головного меню: {e}")

        try:
            text = "🐾 Щось пішло не так. Напиши /start, щоб перезапустити меню."
            if isinstance(event, CallbackQuery):
                await event.message.answer(text)
            elif isinstance(event, Message):
                await event.answer(text)
        except Exception as inner_error:
            logger.error(f"💥 Додаткова помилка при показі fallback-повідомлення: {inner_error}")
