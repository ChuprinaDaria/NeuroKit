# donate.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
import logging

logger = logging.getLogger(__name__)
router = Router()

TEST_MENU = 2  # залишаємо поки так, або замінимо на StatesGroup якщо буде FSM


# ✅ Меню донату (викликається кнопкою)
@router.message(F.text == "💸 Задонатити")
async def donate_from_main_menu(message: Message):
    try:
        keyboard = [
            [InlineKeyboardButton(text="25 грн — маленьке печенько", callback_data="donate_25")],
            [InlineKeyboardButton(text="50 грн — сарделька для котика", callback_data="donate_50")],
            [InlineKeyboardButton(text="150 грн — ліжечко для відпочинку", callback_data="donate_150")],
            [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main")]
        ]

        await message.answer(
            "🐱 Цей бот безкоштовний. Але якщо він був корисний — можеш пригостити мене котячим печивом :)\n\n"
            "Оберіть суму:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    except Exception as e:
        logger.error(f"❌ Помилка в donate_from_main_menu: {e}")
        await message.answer("🐾 Сталася помилка при відкритті меню донату.")


# ✅ Обробка вибору суми
@router.callback_query(F.data.startswith("donate_"))
async def process_donate(callback: CallbackQuery):
    try:
        await callback.answer()
        amount = callback.data.replace("donate_", "")

        payment_links = {
            "25": "https://buy.stripe.com/dR63cJ5c09nVaQw6or",
            "50": "https://buy.stripe.com/dR63cJ5c09nVaQw6or",
            "150": "https://buy.stripe.com/dR63cJ5c09nVaQw6or"
        }

        gift_texts = {
            "25": "коробочку смаколиків",
            "50": "сардельки і лежачок",
            "150": "місячний запас корму"
        }

        payment_link = payment_links.get(amount, payment_links["25"])
        gift_text = gift_texts.get(amount, "приємний подарунок для котика")

        keyboard = [
            [InlineKeyboardButton(text="💳 Підтримати котика", url=payment_link)],
            [InlineKeyboardButton(text="🧪 До тестів", callback_data="back_to_tests")]
        ]

        await callback.message.answer(
            f"🐱 Муррр! Дякую, що вирішили подарувати котику {gift_text}!\n\n"
            f"Натисніть кнопку нижче, щоб здійснити донат через безпечну систему оплати.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    except Exception as e:
        logger.error(f"Помилка обробки донату: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await callback.message.answer("🐱 Сталася помилка при обробці донату. Спробуй пізніше.")
