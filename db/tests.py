import sqlite3
import logging
from config import DB_PATH
import os

logger = logging.getLogger(__name__)


def update_image_filenames_from_folder():
    """Автоматично оновлює image_filename у test_descriptions_cleaned з папки images/"""
    try:
        logger = logging.getLogger(__name__)
        images_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "images"))

        if not os.path.exists(images_dir):
            logger.warning("❌ Папка images не існує!")
            return

        image_files = os.listdir(images_dir)
        logger.info(f"🖼️ Знайдено {len(image_files)} файлів у папці images")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        updated = 0
        for filename in image_files:
            if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                continue

            test_code = os.path.splitext(filename)[0]

            # Шукаємо незалежно від регістру, але залишаємо оригінальний filename
            cursor.execute("SELECT test_code FROM test_descriptions_cleaned WHERE lower(test_code) = ?", (test_code.lower(),))
            result = cursor.fetchone()
            if result:
                cursor.execute("""
                    UPDATE test_descriptions_cleaned 
                    SET image_filename = ?
                    WHERE lower(test_code) = ?
                """, (filename, test_code.lower()))
                updated += 1
                logger.debug(f"✅ Оновлено test_code: {test_code} → {filename}")
            else:
                logger.debug(f"⚠️ Пропущено: {test_code} — не знайдено в БД")

        conn.commit()
        conn.close()

        logger.info(f"✅ Успішно оновлено {updated} записів у БД")

    except Exception:
        logger.exception("❌ Помилка при оновленні image_filename з папки")



# ✅ Отримати мета-інформацію про тест
def get_test_info(test_code: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, developer, use_case, image_filename 
            FROM test_descriptions_cleaned 
            WHERE lower(test_code) = ?
        ''', (test_code.lower(),))
        result = cursor.fetchone()
        conn.close()
        return result if result else (None, None, None, None)
    except Exception as e:
        logger.error(f"❌ Помилка отримання інформації про тест: {e}")
        return (None, None, None, None)

# ✅ Отримати питання та інтерпретації
def get_test_questions(test_code: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (test_code,)
        )
        if not cursor.fetchone():
            logger.warning(f"❌ Таблиця {test_code} не знайдена")
            conn.close()
            return [], []

        cursor.execute(f'''
            SELECT question_id, question_text, answer_text, score, section 
            FROM "{test_code}"
            WHERE question_id IS NOT NULL 
            ORDER BY question_id
        ''')
        questions = cursor.fetchall()

        cursor.execute(f'''
            SELECT interpretation_min, interpretation_max, interpretation_text 
            FROM "{test_code}"
            WHERE interpretation_min IS NOT NULL
        ''')
        interpretations = cursor.fetchall()

        conn.close()
        return questions, interpretations

    except Exception as e:
        logger.error(f"❌ Помилка отримання питань тесту: {e}")
        return [], []

# ✅ Обробка результату тесту
def process_test_result(test_code: str, scores: list, sections: list = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        total_score = sum(scores)
        logger.info(f"🔢 Загальний бал: {total_score}")

        results = []

        if sections:
            section_scores = {}
            for i, score in enumerate(scores):
                section = sections[i]
                section_scores[section] = section_scores.get(section, 0) + score

            for section, score in section_scores.items():
                cursor.execute(f'''
                    SELECT interpretation_text, interpretation_min, interpretation_max 
                    FROM "{test_code}"
                    WHERE (section = ? OR section IS NULL)
                    AND interpretation_min IS NOT NULL AND interpretation_max IS NOT NULL
                ''', (section,))
                interpretations = cursor.fetchall()

                matched = next(
                    (text for text, min_val, max_val in interpretations
                     if float(min_val) <= score <= float(max_val)),
                    None
                )

                if matched:
                    results.append((section, score, matched))

        # ⬇️ Fallback: якщо нічого не знайдено по секціях або їх не було
        if not results:
            cursor.execute(f'''
                SELECT interpretation_text, interpretation_min, interpretation_max 
                FROM "{test_code}"
                WHERE interpretation_min IS NOT NULL AND interpretation_max IS NOT NULL
            ''')
            interpretations = cursor.fetchall()

            matched = next(
                (text for text, min_val, max_val in interpretations
                 if float(min_val) <= total_score <= float(max_val)),
                "Результат не знайдено."
            )
            results = [(None, total_score, matched)]

        conn.close()
        return results

    except Exception as e:
        logger.error(f"❌ Помилка обробки результату тесту: {e}")
        return [(None, 0, "🐾 Сталася помилка при обробці результату.")]
