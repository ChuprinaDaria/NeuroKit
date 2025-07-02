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
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
import os

from config import ADMIN_IDS
from .constants import States, FSMStates
from db.tests import get_test_info
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
async def broadcast_message(bot: Bot, message: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT telegram_id FROM users')
            users = cursor.fetchall()

        success_count = 0
        failed_count = 0
        logger.info(f"Початок розсилки повідомлення для {len(users)} користувачів")

        for user in users:
            chat_id = user[0]
            print(f"🔁 Спроба надіслати користувачу {chat_id}")

            try:
                await bot.send_message(chat_id=chat_id, text=message)
                success_count += 1
                # Додаємо невелику затримку між повідомленнями
                await asyncio.sleep(0.1)
            except Exception as e:
                failed_count += 1
                logger.error(f"Помилка надсилання повідомлення користувачу {chat_id}: {e}")

        logger.info(f"Розсилку завершено. Успішно: {success_count}, Помилок: {failed_count}")
        return success_count, failed_count
    except Exception as e:
        logger.error(f"Глобальна помилка розсилки: {e}")
        logger.error(traceback.format_exc())
        return 0, 0

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

        # Очищаємо всі тимчасові дані
        await state.clear()

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

        await state.set_state(FSMStates.TEST_MENU)
    except Exception as e:
        logger.error(f"Помилка в адмін-панелі: {e}")

# Запуск розсилки
@admin_router.message(F.text == "📢 Надіслати повідомлення всім користувачам")
async def start_broadcast(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            await message.reply("🐱 У вас немає доступу до адмін-панелі.")
            return

        keyboard = [
            [KeyboardButton(text="❌ Скасувати")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

        await message.answer(
            "📢 Введіть повідомлення, яке потрібно надіслати всім користувачам:",
            reply_markup=reply_markup
        )

        await state.set_state(FSMStates.ADMIN_MESSAGE)
    except Exception as e:
        logger.error(f"Помилка підготовки до розсилки: {e}")

# Обробка повідомлення для розсилки
@admin_router.message(StateFilter(FSMStates.ADMIN_MESSAGE))
async def process_broadcast_message(message: Message, state: FSMContext):
    bot = message.bot 
    try:
        if not is_admin(message.from_user.id):
            await message.reply("🐱 У вас немає доступу до адмін-панелі.")
            return

        message_text = message.text
        
        # Логуємо повідомлення
        log_admin_message(message_text)

        wait_message = await message.answer(
            "🕒 Розпочинаю розсилку повідомлення всім користувачам. Це може зайняти деякий час..."
        )

        # Виконуємо розсилку
        success_count, failed_count = await broadcast_message(bot, message_text)

        # Оновлюємо повідомлення про результат
        result_text = f"✅ Розсилку завершено!\n\n"
        result_text += f"📤 Успішно надіслано: {success_count}\n"
        if failed_count > 0:
            result_text += f"❌ Помилок: {failed_count}"

        await wait_message.edit_text(result_text)

        # Повертаємося до адмін-панелі
        await admin_panel(message, state)

    except Exception as e:
        logger.error(f"Помилка під час розсилки: {e}")
        logger.error(traceback.format_exc())
        try:
            await message.answer("❌ Під час розсилки сталася помилка. Перевірте логи для деталей.")
            await admin_panel(message, state)
        except:
            pass

# Скасування розсилки
@admin_router.message(StateFilter(FSMStates.ADMIN_MESSAGE), F.text == "❌ Скасувати")
async def cancel_broadcast(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            await message.reply("🐱 У вас немає доступу до адмін-панелі.")
            return

        await message.answer("❌ Розсилку скасовано.")
        await admin_panel(message, state)
    except Exception as e:
        logger.error(f"Помилка скасування розсилки: {e}")

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

    except Exception as e:
        logger.error(f"Помилка показу статистики: {e}")
        logger.error(traceback.format_exc())
        await message.answer(
            "❌ Під час отримання статистики сталася помилка. Перевірте логи для деталей."
        )

# Обробка кнопки "Назад до головного меню"
@admin_router.message(F.text == "🔙 Назад до головного меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    try:
        if not is_admin(message.from_user.id):
            await message.reply("🐱 У вас немає доступу до адмін-панелі.")
            return

        await message.answer(
            "🔙 Повертаємося до головного меню...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await state.set_state(FSMStates.START)

    except Exception as e:
        logger.error(f"Помилка повернення до головного меню: {e}")

# Функція для реєстрації роутера в основному боті
def setup_admin_router(dp):
    """Функція для підключення адмін-роутера до диспетчера"""
    dp.include_router(admin_router)

router = admin_router