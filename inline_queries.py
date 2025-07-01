# handlers/inline_mode.py

import uuid
import sqlite3
import logging
from aiogram import types
from aiogram.types import (
    InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
)

from config import DB_PATH
from db.phrases import get_random_supportive_phrase

logger = logging.getLogger(__name__)

async def handle_inline_query(inline_query: types.InlineQuery):
    try:
        query = inline_query.query.lower()
        results = []

        if query:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT test_code, name, use_case FROM test_descriptions_cleaned
                WHERE lower(name) LIKE ? OR lower(use_case) LIKE ?
            ''', (f"%{query}%", f"%{query}%"))
            matching_tests = cursor.fetchall()
            conn.close()

            for test_code, name, use_case in matching_tests:
                # Створюємо клавіатуру
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="Пройти в боті", 
                        url=f"https://t.me/Neyrovidminni_kotyki_bot?start=test_{test_code}"
                    )]
                ])
                
                results.append(
                    InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title=name,
                        description=use_case[:100],
                        input_message_content=InputTextMessageContent(
                            message_text=f"*{name}*\n\n{use_case}\n\nПройди тест і дізнайся більше про себе!",
                            parse_mode="Markdown"
                        ),
                        reply_markup=keyboard
                    )
                )

        # Якщо пусто або "підтримка"
        if not query or "підтримка" in query:
            phrase = get_random_supportive_phrase()
            
            # Створюємо клавіатуру для підтримки
            support_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="Відкрити бот", 
                    url="https://t.me/Neyrovidminni_kotyki_bot"
                )]
            ])
            
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="Котик обіймашка",
                    description="Тут, щоб підтримати",
                    input_message_content=InputTextMessageContent(
                        message_text=f"🐱 *Котик обіймашка*\n\n{phrase}\n\n_Від @Neyrovidminni_kotyki_bot_",
                        parse_mode="Markdown"
                    ),
                    reply_markup=support_keyboard
                )
            )

        await inline_query.answer(results)

    except Exception as e:
        logger.error(f"❌ Помилка обробки інлайн-запиту: {e}")

# Хендлер для реєстрації в роутері:
# router.inline_query.register(handle_inline_query)