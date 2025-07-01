import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Filter
from aiogram import F



logger = logging.getLogger(__name__)
router = Router()

# 🌟 Про проєкт
@router.message(F.text == "🐾 Про проєкт")


async def about_project(message: Message):
    try:
        await message.answer(
            "🐱 <b>Про проєкт \"Нейровідмінні котики\"</b>\n\n"
            "Цей бот створено з турботою нейровідмінною людиною — для таких самих, як ти. "
            "Наша мета — підтримати, скерувати й дати змогу краще зрозуміти себе у безпечному просторі.\n\n"
            "📋 У боті ти можеш пройти психологічні тести, які допомагають усвідомити свій стан. "
            "Є інтерпретації результатів, PDF-звіти та навіть ШІ-консультант «Кіт Нейрон», який відповість емпатично і з опорою на доказову психологію.\n\n"
            "🤝 Ми не ставимо діагнозів і не замінюємо спеціалістів — але можемо стати першим кроком на шляху до себе.\n\n"
            "🔧 Проєкт постійно оновлюється: додаємо нові тести, можливості, покращуємо UX і плануємо більше функцій для самопідтримки.\n\n"
            "💌 Якщо хочеш щось запропонувати або поділитись думкою — напиши через /feedback. "
            "Анонімно, без осуду, просто по-людськи.\n\n"
            "🐾 <i>Тут безпечно. Тут про тебе. І тут завжди раді твоїй присутності.</i>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Помилка в about_project: {e}")


# 🌪️ Обробка будь-яких помилок
async def error_handler(event, exception):
    logger.error(f"💥 Сталася помилка: {exception}")

    try:
        if isinstance(event, Message):
            await event.answer(
                "🐱 Ой-ой, сталася помилка. Напиши /start, щоб почати спочатку або дай коту трохи часу 🐾"
            )
    except Exception as e:
        logger.error(f"⚠️ Не вдалося надіслати повідомлення про помилку: {e}")

# 📦 Реєстрація
def register_about_handlers(dp):
    dp.include_router(router)
