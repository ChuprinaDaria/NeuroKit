import asyncio
import sqlite3
import traceback
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter  # Add StateFilter import
from aiogram.fsm.state import State, StatesGroup  # Add these imports if not already present
import os

from config import ADMIN_IDS
from .constants import States
from aiogram.filters import StateFilter

from db.tests import get_test_info  # якщо використовується

from config import DB_PATH

import logging
logger = logging.getLogger(__name__)

# Створюємо роутер для адмін-функцій
admin_router = Router()


# Функція для логування повідомлення адміна
def log_admin_message(message):
    try:
        sent_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO admin_messages_log (message, sent_at) VALUES (?, ?)', (message, sent_at))
        return True
    except Exception as e:
        logger.error(f"Помилка логування повідомлення адміна: {e}")
        return False


# Функція для розсилки повідомлення всім користувачам
async def broadcast_message(bot: Bot, message: str) -> int:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # ✅ Отримуємо тільки валідні telegram_id
            cursor.execute('SELECT telegram_id FROM users WHERE telegram_id IS NOT NULL AND telegram_id > 0')
            users = [int(row[0]) for row in cursor.fetchall() if row[0]]

        success_count = 0
        failed_count = 0
        logger.info(f"📨 Початок розсилки повідомлення для {len(users)} користувачів")

        for chat_id in users:
            try:
                await bot.send_message(chat_id=chat_id, text=message)
                success_count += 1
                await asyncio.sleep(0.1)  # 🕒 затримка для уникнення FloodLimit
            except Exception as e:
                failed_count += 1
                logger.warning(f"❌ [{chat_id}] {type(e).__name__}: {e}")

        logger.info(f"✅ Розсилку завершено. Успішно: {success_count}, Помилок: {failed_count}")
        return success_count

    except Exception as e:
        logger.error(f"💥 Глобальна помилка розсилки: {e}")
        logger.error(traceback.format_exc())
        return 0


# Фільтр для перевірки адмін-прав
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS



# Адмін-панель
@admin_router.message(Command("admin"))
@admin_router.message(F.text == "👑 Адмін-панель")
async def admin_panel(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            await message.reply("🐱 У вас немає доступу до адмін-панелі.")
            return

        keyboard = [
            [KeyboardButton(text="📢 Надіслати повідомлення всім користувачам")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🔙 Назад до головного меню")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

        await message.answer(
            "👑 Адмін-панель\n\nОберіть опцію:",
            reply_markup=reply_markup
        )

        await state.set_state(States.TEST_MENU)
    except Exception as e:
        logger.error(f"Помилка в адмін-панелі: {e}")




@admin_router.message(F.text == "🔙 Назад до головного меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.reply("🐱 У вас немає доступу до адмін-панелі.")
        return

    await message.answer(
        "🔙 Повертаємося до головного меню...",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(States.START)


# Запуск розсилки
@admin_router.message(F.text == "📢 Надіслати повідомлення всім користувачам")
async def start_broadcast(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            await message.reply("🐱 У вас немає доступу до адмін-панелі.")
            return

        # Зберігаємо стан розсилки
        await state.update_data(admin_broadcast_mode=True)
        
        keyboard = [
            [KeyboardButton(text="❌ Скасувати")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

        await message.answer(
            "📢 Введіть повідомлення, яке потрібно надіслати всім користувачам:",
            reply_markup=reply_markup
        )

        await state.set_state(States.ADMIN_MESSAGE)
    except Exception as e:
        logger.error(f"Помилка підготовки до розсилки: {e}")


# Обробка повідомлення для розсилки - FIXED: Use StateFilter
@admin_router.message(StateFilter(States.ADMIN_MESSAGE))
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    try:
        if not is_admin(message.from_user.id):
            await message.reply("🐱 У вас немає доступу до адмін-панелі.")
            return

        user_data = await state.get_data()
        if not user_data.get("admin_broadcast_mode", False):
            logger.warning("Спроба обробки повідомлення не в режимі розсилки")
            await state.set_state(States.TEST_MENU)
            return

        # Очищаємо режим розсилки
        await state.update_data(admin_broadcast_mode=False)

        if message.text == "❌ Скасувати":
            await message.answer("🐱 Розсилку скасовано.")
            await admin_panel(message, state)
            return

        message_text = message.text
        log_admin_message(message_text)

        wait_message = await message.answer("🕒 Розпочинаю розсилку повідомлення всім користувачам. Це може зайняти деякий час...")

        success_count = await broadcast_message(bot, message_text)

        await wait_message.edit_text(
            f"✅ Розсилку завершено! Повідомлення надіслано {success_count} користувачам."
        )

        await admin_panel(message, state)
    except Exception as e:
        logger.error(f"Помилка під час розсилки: {e}")
        logger.error(traceback.format_exc())
        try:
            await message.answer("❌ Під час розсилки сталася помилка. Перевірте логи для деталей.")
        except:
            pass
        await admin_panel(message, state)


# Показ статистики
@admin_router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            await message.reply("🐱 У вас немає доступу до адмін-панелі.")
            return

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Загальна кількість користувачів
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            # Загальна кількість пройдених тестів
            cursor.execute("SELECT SUM(tests_completed) FROM users")
            total_tests = cursor.fetchone()[0] or 0

            # Найпопулярніші тести
            cursor.execute("""
                SELECT last_test, COUNT(*) as count
                FROM users
                WHERE last_test IS NOT NULL
                GROUP BY last_test
                ORDER BY count DESC
                LIMIT 5
            """)
            popular_tests = cursor.fetchall()

            # Нові користувачі за день
            cursor.execute("""
                SELECT COUNT(*) FROM users
                WHERE date_joined >= datetime('now', '-1 day')
            """)
            new_users_day = cursor.fetchone()[0]

            # Нові користувачі за тиждень
            cursor.execute("""
                SELECT COUNT(*) FROM users
                WHERE date_joined >= datetime('now', '-7 day')
            """)
            new_users_week = cursor.fetchone()[0]

            # Кількість питань до ШІ
            cursor.execute("SELECT SUM(questions_asked) FROM ai_usage")
            total_questions = cursor.fetchone()[0] or 0

            # Кількість консультацій
            cursor.execute("SELECT SUM(consultations_used) FROM ai_usage")
            total_consults = cursor.fetchone()[0] or 0

        # Формування тексту
        stats_text = (
            f"📊 *Статистика бота*\n\n"
            f"👥 Загальна кількість користувачів: {total_users}\n"
            f"📝 Всього пройдено тестів: {total_tests}\n"
            f"🆕 Нових користувачів за день: {new_users_day}\n"
            f"🆕 Нових користувачів за тиждень: {new_users_week}\n\n"
            f"🤖 *Користування ШІ:*\n"
            f"- Питань до ШІ: {total_questions}\n"
            f"- Консультацій: {total_consults}\n\n"
        )

        if popular_tests:
            stats_text += "🔝 *Найпопулярніші тести:*\n"
            for test_code, count in popular_tests:
                test_name, *_ = get_test_info(test_code) or (test_code, )
                stats_text += f"- {test_name}: {count} разів\n"

        await message.answer(stats_text, parse_mode="Markdown")
        await state.set_state(States.TEST_MENU)

    except Exception as e:
        logger.error(f"Помилка показу статистики: {e}")
        logger.error(traceback.format_exc())

        await message.answer(
            "❌ Під час отримання статистики сталася помилка. Перевірте логи для деталей."
        )
        await state.set_state(States.TEST_MENU)



# Обробка кнопки "Назад до головного меню"
@admin_router.message(F.text == "🔙 Назад до головного меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            await message.reply("🐱 У вас немає доступу до адмін-панелі.")
            return

        # Тут можна викликати функцію головного меню
        # Наприклад: await main_menu(message, state)
        
        await message.answer(
            "🔙 Повертаємося до головного меню...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await state.set_state(States.START)
    except Exception as e:
        logger.error(f"Помилка повернення до головного меню: {e}")

@admin_router.message(F.text == "❌ Скасувати")
async def cancel_broadcast(message: Message, state: FSMContext):
    user_data = await state.get_data()
    if user_data.get("admin_broadcast_mode"):
        await state.update_data(admin_broadcast_mode=False)
        await message.answer("❌ Розсилку скасовано.", reply_markup=ReplyKeyboardRemove())
        await admin_panel(message, state)
    else:
        await message.answer("ℹ️ Нічого не скасовуємо, бо немає активної розсилки.")


# Функція для реєстрації роутера в основному боті
def setup_admin_router(dp):
    """Функція для підключення адмін-роутера до диспетчера"""
    dp.include_router(admin_router)

router = admin_router
