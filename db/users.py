import sqlite3
import traceback
import logging
from datetime import datetime
from config import DB_PATH, ADMIN_IDS


logger = logging.getLogger(__name__)

def add_user(telegram_id, phone, username=None, first_name=None, last_name=None):
    try:
        date_joined = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT telegram_id FROM users WHERE telegram_id = ?', (telegram_id,))
            if cursor.fetchone():
                logger.info(f"Користувач {telegram_id} вже існує в базі даних")
                return True

            cursor.execute('''
                INSERT INTO users 
                (telegram_id, phone, username, first_name, last_name, date_joined) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (telegram_id, phone, username, first_name, last_name, date_joined))
            logger.info(f"Користувач {telegram_id} успішно доданий до бази даних")
            return True
    except Exception as e:
        logger.error(f"Помилка додавання користувача: {e}")
        logger.error(traceback.format_exc())
        return False

def update_user_stats(telegram_id, test_code=None, started=False, completed=False):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if started:
                cursor.execute('UPDATE users SET tests_started = tests_started + 1 WHERE telegram_id = ?', (telegram_id,))
            if completed:
                cursor.execute('UPDATE users SET tests_completed = tests_completed + 1 WHERE telegram_id = ?', (telegram_id,))
            if test_code:
                cursor.execute('UPDATE users SET last_test = ? WHERE telegram_id = ?', (test_code, telegram_id))
            return True
    except Exception as e:
        logger.error(f"Помилка оновлення статистики користувача: {e}")
        return False

def can_use_ai_today(telegram_id):
    today = datetime.now().strftime('%Y-%m-%d')

    if telegram_id in ADMIN_IDS:
        logger.info(f"[AI] Адміну {telegram_id} дозволено без ліміту")
        return True, 0

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT consultations_used, questions_asked FROM ai_usage
                WHERE telegram_id = ? AND date = ?
            ''', (telegram_id, today))
            row = cursor.fetchone()

            if not row:
                logger.info(f"[AI] Користувач {telegram_id} — новий на сьогодні. Ліміт 0.")
                return True, 0

            consultations, questions = row
            consultations = consultations or 0
            questions = questions or 0

            allowed = consultations < 3
            logger.info(f"[AI] {telegram_id}: {consultations=}, {questions=}, {allowed=}")
            return allowed, questions

    except Exception as e:
        logger.exception(f"[AI] ❌ Помилка перевірки AI-лімітів для {telegram_id}")
        return False, 0

def update_ai_usage(telegram_id, questions_added=0, mark_consulted=False):
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT consultations_used, questions_asked FROM ai_usage WHERE telegram_id = ? AND date = ?',
                (telegram_id, today)
            )
            row = cursor.fetchone()

            if row:
                consultations_used, questions_asked = row
                consultations_used = consultations_used or 0
                questions_asked = questions_asked or 0

                if mark_consulted:
                    cursor.execute('''
                        UPDATE ai_usage
                        SET consultations_used = ?
                        WHERE telegram_id = ? AND date = ?
                    ''', (consultations_used + 1, telegram_id, today))

                if questions_added:
                    cursor.execute('''
                        UPDATE ai_usage
                        SET questions_asked = ?
                        WHERE telegram_id = ? AND date = ?
                    ''', (questions_asked + questions_added, telegram_id, today))
            else:
                cursor.execute('''
                    INSERT INTO ai_usage (telegram_id, date, consultations_used, questions_asked)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, today, int(mark_consulted), questions_added))

            conn.commit()

    except Exception as e:
        logger.exception(f"[AI] ❌ Помилка оновлення лімітів для {telegram_id}")


def is_user_registered(telegram_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT telegram_id FROM users WHERE telegram_id = ?', (telegram_id,))
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Помилка перевірки реєстрації користувача: {e}")
        return False
