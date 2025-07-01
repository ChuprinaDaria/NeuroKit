import logging
import asyncio
import os
import sqlite3
import traceback

from aiogram import Bot, Dispatcher, Router
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommandScopeDefault, ErrorEvent
from aiogram.filters import Command 

from config import BOT_TOKEN, DB_PATH
from handlers import register_all_handlers
from inline_queries import handle_inline_query  # інлайн-пошук
from db.tests import update_image_filenames_from_folder
from handlers.about import register_about_handlers


# ====== Ініціалізація бази ======
def init_db():
    try:
        logging.info(f"🔗 Підключення до БД: {DB_PATH}")
        if not os.path.exists(DB_PATH):
            logging.warning(f"❌ БД не знайдено: {DB_PATH}")
            return False

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            logging.info(f"📦 Таблиці: {[x[0] for x in cursor.fetchall()]}")
        return True
    except Exception:
        logging.exception("💥 Помилка ініціалізації БД")
        return False


# ====== Глобальний обробник помилок ======
async def error_handler(event: ErrorEvent):
    try:
        logging.error(f"❌ Помилка: {event.exception}")
        logging.error(f"❌ Трейсбек: {traceback.format_exc()}")

        if event.update and event.update.message:
            try:
                await event.update.message.reply(
                    "🐱 Вибач, сталася помилка. Спробуй пізніше або звернись до адміністратора."
                )
            except Exception as e:
                logging.error(f"❌ Не вдалося відправити повідомлення про помилку: {e}")
        elif event.update and event.update.callback_query:
            try:
                await event.update.callback_query.message.reply(
                    "🐱 Вибач, сталася помилка. Спробуй пізніше або звернись до адміністратора."
                )
            except Exception as e:
                logging.error(f"❌ Не вдалося відправити повідомлення про помилку: {e}")

    except Exception as e:
        logging.error(f"❌ Помилка в error_handler: {e}")


def register_inline_handlers(dp: Dispatcher):
    """Реєстрація хендлерів для інлайн-режиму"""
    router = Router()
    router.inline_query.register(handle_inline_query)
    dp.include_router(router)


# ====== Основна функція ======
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Ініціалізація БД
    # Ініціалізація БД
    if not init_db():
        logging.error("❌ Не вдалося ініціалізувати БД. Бот може працювати некоректно.")
    else:
        from db.tests import update_image_filenames_from_folder
        update_image_filenames_from_folder()


    # Створення бота із новим синтаксисом для parse_mode
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # ✅ Реєстрація основних хендлерів
    register_all_handlers(dp)

    # ✅ Реєстрація інлайн-хендлерів
    register_inline_handlers(dp)

    # ✅ Глобальний обробник помилок
    dp.errors.register(error_handler)

    
    # Встановлення команд бота (опціонально)
    try:
        from aiogram.types import BotCommand

        commands = [
            BotCommand(command="start", description="🏠 Головне меню"),
            BotCommand(command="feedback", description="📝 Написати відгук"),
            BotCommand(command="help", description="❓ Допомога"),
            
        ]
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logging.info("✅ Команди бота встановлено")
    except Exception as e:
        logging.warning(f"⚠️ Не вдалося встановити команди бота: {e}")

    logging.info("🚀 Бот запущено")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logging.info("🛑 Бот зупинено користувачем")
    except Exception as e:
        logging.error(f"❌ Критична помилка: {e}")
    finally:
        await bot.session.close()
        logging.info("🔚 Сесія бота закрита")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 Програма завершена користувачем")
    except Exception as e:
        logging.error(f"❌ Фатальна помилка: {e}")
        traceback.print_exc()
