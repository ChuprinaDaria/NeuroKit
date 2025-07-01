# share_friend.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
import logging
import traceback
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

logger = logging.getLogger(__name__)
router = Router()

# Головне меню поширення
SHARE_TEXT = (
    "Привіт! Я хочу поділитися з тобою ботом @Neyrovidminni_kotyki_bot.\n\n"
    "Це бот для проходження психологічних тестів українською мовою з мʼякими формулюваннями "
    "і підтримкою від милих котиків! Це допомогло мені, можливо допоможе і тобі 🐱"
)




@router.message(F.text == "🤝 Поділитись з другом")
async def share_from_menu(message: Message):
    try:
        keyboard = [
            [InlineKeyboardButton(text="📲 Надіслати другу", switch_inline_query=SHARE_TEXT)],
            [InlineKeyboardButton(text="🔗 Скопіювати посилання", callback_data="copy_link")],
            [InlineKeyboardButton(text="⬅️ Назад до тестів", callback_data="back_to_tests")]
        ]

        await message.answer(
            "🐱 Розповісти друзям про Нейровідмінних котиків?\n\n"
            "Ви можете поділитися ботом за допомогою кнопки нижче. "
            "Котики будуть дуже вдячні за поширення! 💙💛",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    except Exception as e:
        logger.error(f"❌ Помилка в share_from_menu: {e}")
        await message.answer("🐾 Сталася помилка. Спробуй ще раз.")



@router.callback_query(F.data == "copy_link")
async def copy_link(callback: CallbackQuery):
    try:
        await callback.answer("Посилання скопійовано: https://t.me/Neyrovidminni_kotyki_bot", show_alert=True)

        await callback.message.answer(
            "🔗 Ось посилання на бота для копіювання:\n\n"
            "https://t.me/Neyrovidminni_kotyki_bot"
        )

    except Exception as e:
        logger.error(f"Помилка копіювання посилання: {e}")
        logger.error(traceback.format_exc())
        await callback.message.answer("🐱 Сталася помилка при копіюванні. Спробуй ще раз.")
