# start_phone_main.py
import logging
from aiogram import Router, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.users import is_user_registered, add_user
from config import ADMIN_IDS
from handlers.menu import show_main_menu

logger = logging.getLogger(__name__)
router = Router()

# === Стан для FSM ===
class RegistrationStates(StatesGroup):
    waiting_for_phone = State()


# === /start ===
@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id

        if is_user_registered(user_id):
            return await show_main_menu(message, state)
        else:
            keyboard = [
                [KeyboardButton(text="📱 Поділитися номером", request_contact=True)]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

            await message.answer(
                "🐱 Привіт! Я — котик-помічник. Поділись номером телефону для авторизації 🐾",
                reply_markup=reply_markup
            )
            await state.set_state(RegistrationStates.waiting_for_phone)
    except Exception as e:
        logger.error(f"❌ Помилка в start_handler: {e}")
        await message.answer("🐾 Щось пішло не так. Напиши /start ще раз.")


# === Обробка номера телефону ===
@router.message(F.contact)
async def process_phone(message: Message, state: FSMContext):
    try:
        contact = message.contact
        if not contact:
            await message.answer("🐾 Номер не отримано. Спробуй ще раз /start")
            return

        user = message.from_user
        phone = contact.phone_number
        logger.info(f"📲 Отримано номер: {phone} від {user.id}")

        add_user(user.id, phone, user.username, user.first_name, user.last_name)

        for admin_id in ADMIN_IDS:
            try:
                await message.bot.send_message(
                    chat_id=admin_id,
                    text=f"🆕 Новий користувач: {user.first_name} (@{user.username})"
                )
            except Exception as e:
                logger.warning(f"⚠️ Не вдалося повідомити адміна {admin_id}: {e}")

        await message.answer(
            "✅ Дякую за реєстрацію! Відкриваю головне меню.",
            reply_markup=ReplyKeyboardRemove()
        )
        await show_main_menu(message, state)
    except Exception as e:
        logger.error("❌ Помилка в process_phone")
        await message.answer("🐱 Сталася помилка. Напишіть /start ще раз 🙏")
