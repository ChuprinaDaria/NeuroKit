from aiogram import Bot, types, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.filters.callback_data import CallbackData

from db.tests import get_test_info, get_test_questions
from db.users import update_user_stats
from db.tests import process_test_result
from db.phrases import get_random_supportive_phrase
from handlers.menu import show_main_menu
import logging
import sqlite3
import os
import traceback
from config import DB_PATH
import re
from aiogram.types import FSInputFile
from aiogram import F



# Ініціалізуємо роутер
router = Router()
logger = logging.getLogger(__name__)

# Припускаючи, що DB_PATH визначений в константах
# from .constants import DB_PATH


def escape_md_v2(text: str) -> str:
    """
    Escape all MarkdownV2 special characters according to Telegram rules
    """
    if not text:
        return ""
    
    # Telegram MarkdownV2 спецсимволи
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', text)

def bold_v2(text: str) -> str:
    return f"*{escape_md_v2(text)}*"

def italic_v2(text: str) -> str:
    return f"_{escape_md_v2(text)}_"



def escape_md(text: str) -> str:
    """
    Екранує спеціальні символи для звичайного Markdown
    """
    if not text:
        return ""
    
    # Символи, які потрібно екранувати в звичайному Markdown
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', text)


def escape_md_v2_regex(text: str) -> str:
    """
    Екранує спеціальні символи для MarkdownV2 використовуючи регулярні вирази
    """
    if not text:
        return ""
    
    # Символи, які потрібно екранувати в MarkdownV2
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', text)


# Функція для безпечного форматування тексту з жирним шрифтом
def format_bold_safe(text: str) -> str:
    """
    Безпечно форматує текст жирним шрифтом, екранувавши спеціальні символи
    """
    if not text:
        return ""
    return f"*{escape_md_v2(text)}*"


# Функція для безпечного форматування тексту курсивом
def format_italic_safe(text: str) -> str:
    """
    Безпечно форматує текст курсивом, екранувавши спеціальні символи
    """
    if not text:
        return ""
    return f"_{escape_md_v2(text)}_"



class TestStates(StatesGroup):
    test_menu = State()
    test_in_progress = State()

# Callback data фабрики для типізації
class TestCallbackData(CallbackData, prefix="test"):
    action: str
    test_code: str = ""

class AnswerCallbackData(CallbackData, prefix="answer"):
    question_idx: int
    score: float
    section: str = ""


@router.message(F.text == "🧪 Пройти тест")
async def show_test_menu_from_button(message: Message, state: FSMContext):
    await state.clear()  # Щоб обнулити будь-який попередній стан
    await show_test_list(message, state)

@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await show_main_menu(callback, state)




@router.callback_query(lambda c: c.data.startswith("test_"))
async def test_info_handler(callback: CallbackQuery, state: FSMContext):
    """Хендлер для показу інформації про тест"""
    await test_info(callback, state)

@router.callback_query(lambda c: c.data == "back_to_tests")
async def back_to_tests_handler(callback: CallbackQuery, state: FSMContext):
    """Хендлер для повернення до списку тестів"""
    await back_to_tests(callback, state)

@router.callback_query(lambda c: c.data.startswith("start_test_"))
async def start_test_handler(callback: CallbackQuery, state: FSMContext):
    """Хендлер для запуску тесту"""
    await start_test(callback, state)

@router.callback_query(lambda c: c.data.startswith("answer_"), StateFilter(TestStates.test_in_progress))
async def process_answer_handler(callback: CallbackQuery, state: FSMContext):
    """Хендлер для обробки відповідей на питання"""
    await process_answer(callback, state)

@router.callback_query(lambda c: c.data == "share_test_text")
async def share_test_text_handler(callback: CallbackQuery, state: FSMContext):
    """Хендлер для поширення тексту тесту"""
    await share_test_text(callback, state)

@router.callback_query(lambda c: c.data == "copy_share_text")
async def copy_share_text_handler(callback: CallbackQuery, state: FSMContext):
    """Хендлер для копіювання тексту поширення"""
    await copy_share_text(callback, state)

@router.callback_query(lambda c: c.data == "back_to_results")
async def back_to_results_handler(callback: CallbackQuery, state: FSMContext):
    """Хендлер для повернення до результатів"""
    await back_to_results(callback, state)

# Основні функції (без змін в логіці)
async def show_test_list(message: Message, state: FSMContext):
    try:
        # Припускаючи, що DB_PATH визначений глобально або імпортований


        
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Виводимо всі таблиці для діагностики
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"Таблиці в базі даних: {[table[0] for table in tables]}")
        
        # Перевіряємо структуру таблиці test_descriptions_cleaned
        try:
            cursor.execute("PRAGMA table_info(test_descriptions_cleaned)")
            columns = cursor.fetchall()
            logger.info(f"Структура таблиці test_descriptions_cleaned: {columns}")
        except Exception as e:
            logger.error(f"Помилка отримання структури таблиці: {e}")
        
        # Перевіряємо кількість записів
        cursor.execute('SELECT COUNT(*) FROM test_descriptions_cleaned')
        count = cursor.fetchone()[0]
        logger.info(f"Кількість тестів у базі даних: {count}")
        
        # Отримуємо перший запис для перевірки
        cursor.execute('SELECT * FROM test_descriptions_cleaned LIMIT 1')
        sample = cursor.fetchone()
        logger.info(f"Приклад запису тесту: {sample}")
        
        # Тепер запит для меню
        cursor.execute('SELECT test_code, name, use_case FROM test_descriptions_cleaned ORDER BY name')
        tests = cursor.fetchall()
        
        conn.close()
        
        if not tests:
            # Якщо тестів немає, пропонуємо додати тестовий запис
            logger.warning("Тести не знайдено в базі даних")
            
            # Додаємо демо-тест, якщо тестів немає
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Перевіряємо, чи вже існує запис з таким кодом
            cursor.execute('SELECT test_code FROM test_descriptions_cleaned WHERE test_code = ?', ('gad7',))
            if not cursor.fetchone():
                cursor.execute('''
                INSERT INTO test_descriptions_cleaned 
                (test_code, name, developer, use_case, description, image_filename) 
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    'gad7', 
                    'GAD-7 Тест на тривожність', 
                    'Spitzer et al.', 
                    'Скринінг генералізованого тривожного розладу', 
                    'Цей короткий тест допомагає оцінити рівень тривожності за останні 2 тижні.', 
                    'gad7.jpg'
                ))
                conn.commit()
                logger.info("Додано демо-тест GAD-7")
            
            conn.close()
            
            await message.answer(
                "🐱 Наразі у базі даних відсутні тести. Додано демо-тест GAD-7. Спробуйте оновити список."
            )
            return
        
        # Створюємо інлайн-кнопки для вибору тесту
        keyboard = []
        for test_code, name, description in tests:
            if description:
                short_desc = description[:30] + "..." if len(description) > 30 else description
                keyboard.append([InlineKeyboardButton(text=f"{name} — {short_desc}", callback_data=f"test_{test_code}")])
            else:
                keyboard.append([InlineKeyboardButton(text=f"{name}", callback_data=f"test_{test_code}")])
        
        keyboard.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await message.answer(
            "🧪 Оберіть тест, який хочете пройти:",
            reply_markup=reply_markup
        )
        
        await state.set_state(TestStates.test_menu)
        
    except Exception as e:
        logger.error(f"Помилка показу списку тестів: {e}")
        await message.answer(
            "🐱 На жаль, сталася помилка при завантаженні списку тестів. Спробуйте ще раз."
        )

async def test_info(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()

        if callback.data == "back_to_main":
            await callback.message.delete()
            return await show_main_menu(callback.message, state)

        test_code = callback.data.replace("test_", "")
        name, developer, use_case, image_filename = get_test_info(test_code)

        if not name:
            await callback.message.answer("🐱 Вибач, інформація про цей тест не знайдена.")
            return

        await state.update_data(test_code=test_code)

        # ✅ Розмітка для опису
        caption = (
            f"{bold_v2(name)}\n\n"
            f"{italic_v2('Розробник(и)')}: {escape_md_v2(developer)}\n"
            f"{italic_v2('Застосування')}: {escape_md_v2(use_case)}\n\n"
            "Натисни кнопку, щоб почати тест ⬇"
        )

        # ✅ Клавіатура
        keyboard = [
            [InlineKeyboardButton(text="🧪 Почати тест", callback_data=f"start_test_{test_code}")],
            [InlineKeyboardButton(text="⬅ Назад до списку тестів", callback_data="back_to_tests")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        # ✅ Завантаження фото (якщо є)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(base_dir, "..", "images", image_filename) if image_filename else None

        if image_filename and os.path.exists(image_path):
            logger.info(f"📸 Відправляємо фото: {image_path}")
            photo = FSInputFile(image_path)

            await callback.message.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )
        else:
            if image_filename:
                logger.warning(f"⚠️ Зображення не знайдено: {image_path}")

            await callback.message.answer(
                text=caption,
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )

        await callback.message.delete()

    except Exception as e:
        logger.error(f"❌ Помилка показу інформації про тест: {e}")
        try:
            await callback.message.answer("🐾 Сталася помилка. Спробуй ще раз пізніше.")
        except Exception as inner_error:
            logger.error(f"❌ Неможливо надіслати fallback повідомлення: {inner_error}")

async def back_to_tests(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        
        # Видаляємо поточне повідомлення
        try:
            await callback.message.delete()
        except:
            pass
        
        
        
        # Отримуємо список тестів напряму
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Запит для меню
        cursor.execute('SELECT test_code, name, use_case FROM test_descriptions_cleaned ORDER BY name')
        tests = cursor.fetchall()
        
        conn.close()
        
        # Створюємо інлайн-кнопки для вибору тесту
        keyboard = []
        for test_code, name, description in tests:
            if description:
                short_desc = description[:30] + "..." if len(description) > 30 else description
                keyboard.append([InlineKeyboardButton(text=f"{name} — {short_desc}", callback_data=f"test_{test_code}")])
            else:
                keyboard.append([InlineKeyboardButton(text=f"{name}", callback_data=f"test_{test_code}")])
        
        keyboard.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Надсилаємо повідомлення зі списком тестів
        await callback.message.answer(
            text="🧪 Оберіть тест, який хочете пройти:",
            reply_markup=reply_markup
        )
        
        await state.set_state(TestStates.test_menu)
        
    except Exception as e:
        logger.error(f"Помилка повернення до списку тестів: {e}")
        logger.error(traceback.format_exc())
        
        try:
            await callback.message.answer(
                text="🐱 На жаль, сталася помилка. Спробуйте написати /start для перезапуску."
            )
        except:
            pass

async def start_test(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()

        test_code = callback.data.replace("start_test_", "")
        logger.info(f"Запуск тесту: {test_code}")

        questions, interpretations = get_test_questions(test_code)

        logger.info(f"Отримано питань: {len(questions)}, інтерпретацій: {len(interpretations)}")

        if not questions:
            await callback.message.answer("🐱 Вибачте, питання для цього тесту не знайдені.")
            return

        # Отримуємо унікальні question_id
        unique_ids = []
        seen = set()
        for row in questions:
            qid = row[0]
            if qid not in seen:
                unique_ids.append(qid)
                seen.add(qid)

        # Ініціалізуємо дані для проходження тесту
        await state.update_data(
            test_code=test_code,
            questions=questions,
            question_ids=unique_ids,
            current_question=0,
            answers=[],
            scores=[],
            sections=[],
            interpretations=interpretations
        )

        # Оновлюємо статистику користувача
        update_user_stats(callback.from_user.id, test_code=test_code, started=True)

        # Видаляємо попереднє повідомлення
        await callback.message.delete()

        # Показуємо перше питання
        return await show_question(callback.message, state)

    except Exception as e:
        logger.error(f"Помилка запуску тесту: {e}")
        import traceback
        logger.error(traceback.format_exc())

        try:
            await callback.message.answer(
                "🐱 На жаль, сталася помилка при запуску тесту. Спробуйте ще раз."
            )
        except:
            pass

async def show_question(message: Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        if not user_data or "questions" not in user_data or "question_ids" not in user_data:
            logger.error("Відсутні дані тесту в контексті")
            await message.answer(
                "🐱 Помилка. Спробуйте почати тест спочатку."
            )
            return

        all_rows = user_data["questions"]
        question_ids = user_data["question_ids"]
        current_index = user_data.get("current_question", 0)

        if current_index >= len(question_ids):
            return await show_result(message, state)

        current_qid = question_ids[current_index]
        current_block = [row for row in all_rows if row[0] == current_qid]

        if not current_block:
            logger.warning(f"Нема питань з ID {current_qid}")
            return await show_result(message, state)

        question_text = current_block[0][1]
        section = current_block[0][4]  # section може бути None

        keyboard = []
        for row in current_block:
            answer_text = row[2]
            score = row[3]
            try:
                score_float = float(score)
            except:
                score_float = 0.0

            callback_data = f"answer_{current_index}_{score_float}"
            if section:
                callback_data += f"_{section}"

            keyboard.append([InlineKeyboardButton(text=answer_text, callback_data=callback_data)])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        await message.answer(
            text=f"❓ {question_text}",
            reply_markup=reply_markup
        )

        await state.set_state(TestStates.test_in_progress)

    except Exception as e:
        logger.error(f"Помилка в show_question: {e}")
        await message.answer(
            "😿 Помилка при показі питання. Спробуйте пізніше."
        )

async def process_answer(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        
        callback_data = callback.data.split('_')
        if len(callback_data) >= 3:
            question_idx = int(callback_data[1])
            score = float(callback_data[2])
            section = callback_data[3] if len(callback_data) > 3 else None
            
            # Отримуємо поточні дані
            user_data = await state.get_data()
            
            # Перевіряємо наявність даних
            if "answers" not in user_data or "scores" not in user_data:
                user_data["answers"] = []
                user_data["scores"] = []
                user_data["sections"] = []
            
            # Отримуємо текст відповіді з кнопки
            answer_text = ""
            for row in callback.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.callback_data == callback.data:
                        answer_text = button.text
                        break
            
            user_data["answers"].append(answer_text)
            user_data["scores"].append(score)
            if section:
                if "sections" not in user_data:
                    user_data["sections"] = []
                user_data["sections"].append(section)
            
            # Переходимо до наступного питання
            user_data["current_question"] += 1
            
            # Оновлюємо стан
            await state.update_data(**user_data)
            
            # Видаляємо попереднє повідомлення
            await callback.message.delete()
            
            # Показуємо наступне питання або результат
            return await show_question(callback.message, state)
    
    except Exception as e:
        logger.error(f"Помилка обробки відповіді: {e}")
        
        try:
            await callback.message.answer(
                "🐱 На жаль, сталася помилка при обробці вашої відповіді. Спробуйте пройти тест знову."
            )
        except:
            pass

async def show_result(message: Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        if not user_data or "test_code" not in user_data or "scores" not in user_data:
            logger.error("Відсутні дані для показу результату")
            await message.answer(
                "🐱 На жаль, сталася помилка при обробці результатів. Спробуйте пройти тест знову."
            )
            return

        test_code = user_data["test_code"]
        scores = user_data["scores"]
        sections = user_data.get("sections") or None

        # Обробка результату
        result = process_test_result(test_code, scores, sections)
        total_score = sum(scores)

        # Оновлюємо дані стану
        await state.update_data(
            test_name=get_test_info(test_code)[0] if get_test_info(test_code) else "Тест"
        )

        # Назва тесту
        test_info = get_test_info(test_code)
        name = test_info[0] if test_info and len(test_info) > 0 else "Тест"
        
        result_text = f"📊 *Результати тесту {name}*\n\n"

        # Зберігаємо короткий результат для посилання
        short_result = ""
        for section, score, interpretation in result:
            score = round(score, 1)
            if section:
                result_text += f"*{section.capitalize()}*: {score} балів\n"
                short_result += f"{section.capitalize()}: {score} балів, "
            else:
                result_text += f"*Загальний бал*: {score}\n"
                short_result = f"{score} балів"
            result_text += f"_{interpretation}_\n\n"
            
        # Видаляємо останню кому, якщо вона є
        if short_result.endswith(", "):
            short_result = short_result[:-2]

        # Фраза підтримки
        result_text += f"🐱 {get_random_supportive_phrase()}\n\n"

        # Перевірка на "високий бал"
        is_high_score = (
            (test_code == "gad7" and total_score > 10)
            or (test_code == "phq9" and total_score > 10)
            or (test_code == "pcl5" and total_score > 33)
            or (test_code.lower() == "aq" and total_score > 32)
            or (test_code.lower() == "bdi-ii" and total_score > 20)
            or (test_code.lower() == "stai" and total_score > 40)
        )

        # Статистика
        update_user_stats(message.from_user.id, completed=True)

        # Кнопки
        keyboard = []
        
        # PDF-звіт
        keyboard.append([InlineKeyboardButton(text="📄 Експорт у PDF для лікаря", callback_data="pdf_report")])
        # ШІ-консультація
        keyboard.append([InlineKeyboardButton(text="🤖 Консультація з ШІ", callback_data="ask_ai")])

        # Створюємо текст для поширення (без URL)
        share_text = f"Привіт! Я пройшов тест {name} у @Neyrovidminni_kotyki_bot.\nМій результат: {short_result}.\nХочеш дізнатися свій? Переходь за посиланням:"
        bot_link = f"https://t.me/Neyrovidminni_kotyki_bot?start=test_{test_code}"
        
        # Зберігаємо повний текст для копіювання
        full_share_text = f"{share_text}\n{bot_link}"
        await state.update_data(share_text=full_share_text)
        
        # Кнопка для отримання тексту для поширення
        keyboard.append([InlineKeyboardButton(text="🤝 Порадити тест другу", callback_data="share_test_text")])
        
        # Донат
        keyboard.append([InlineKeyboardButton(text="💸 Підтримати проект", callback_data="donate_5")])
        
        # Нові тести
        keyboard.append([InlineKeyboardButton(text="🧪 Інші тести", callback_data="back_to_tests")])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        await message.answer(
            text=result_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        await state.set_state(TestStates.test_menu)

    except Exception as e:
        logger.error(f"Помилка показу результату тесту: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await message.answer(
                "🐱 На жаль, сталася помилка при показі результатів. Спробуйте пройти тест знову."
            )
        except:
            pass

async def share_test_text(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        
        user_data = await state.get_data()
        share_text = user_data.get("share_text", "")
        if not share_text:
            # Якщо текст недоступний, створюємо загальний
            share_text = "Привіт! Спробуй пройти психологічні тести з підтримкою від котиків у @Neyrovidminni_kotyki_bot"
        
        # Створюємо клавіатуру з кнопками
        keyboard = [
            [InlineKeyboardButton(text="📱 Поширити через Telegram", switch_inline_query=share_text)],
            [InlineKeyboardButton(text="📋 Скопіювати текст", callback_data="copy_share_text")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_results")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.answer(
            "🐱 Як би ви хотіли поділитися тестом з другом?",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Помилка при створенні меню поширення: {e}")
        await callback.message.answer("🐱 На жаль, сталася помилка. Спробуйте ще раз.")

async def copy_share_text(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer("Текст скопійовано у буфер обміну")
        
        user_data = await state.get_data()
        share_text = user_data.get("share_text", "")
        test_code = user_data.get("test_code", "")
        
        if share_text:
            await callback.message.answer(
                f"🐱 Ось текст для копіювання:\n\n{share_text}\n\n"
                f"Скопіюйте цей текст і надішліть його другу."
            )
        else:
            await callback.message.answer("🐱 На жаль, текст для поширення недоступний. Спробуйте пройти тест знову.")
    except Exception as e:
        logger.error(f"Помилка копіювання тексту: {e}")
        await callback.message.answer("🐱 На жаль, сталася помилка при копіюванні тексту.")

async def back_to_results(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        
        # Видаляємо поточне повідомлення
        await callback.message.delete()
        
    except Exception as e:
        logger.error(f"Помилка повернення до результатів: {e}")