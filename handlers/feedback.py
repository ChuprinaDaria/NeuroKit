from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import os
from dotenv import load_dotenv
from config import ADMIN_IDS

load_dotenv()
router = Router()
logger = logging.getLogger(__name__)

# 👤 ID адміна
ADMIN_ID = ADMIN_IDS[0] 

class FeedbackStates(StatesGroup):
    waiting_feedback = State()

@router.message(F.text == "/feedback")
async def ask_for_feedback(message: Message, state: FSMContext):
    await state.set_state(FeedbackStates.waiting_feedback)
    await message.answer("✍ Напиши свій відгук або побажання. Він буде анонімно переданий адміну.")

@router.message(FeedbackStates.waiting_feedback)
async def receive_feedback(message: Message, state: FSMContext):
    feedback = message.text.strip()

    # Надсилання адміну
    try:
        text = (
            "📩 *Новий анонімний відгук від користувача:*\n\n"
            f"{feedback}"
        )
        await message.bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="Markdown")
        await message.answer("✅ Дякуємо! Твій відгук надіслано 💌")
    except Exception as e:
        logger.exception("❌ Не вдалося надіслати відгук адміну")
        await message.answer("❌ Упс! Щось пішло не так...")

    await state.clear()
