from aiogram import types
from aiogram.fsm.context import FSMContext
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import datetime
import os
import logging
from aiogram import Router, F
from db.tests import get_test_info, process_test_result  # припускаємо, що ці утиліти вже винесені

logger = logging.getLogger(__name__)

async def pdf_report(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.answer()

        # Отримуємо дані з FSM
        data = await state.get_data()
        test_code = data.get("test_code", "")
        questions = data.get("questions", [])
        answers = data.get("answers", [])
        scores = data.get("scores", [])
        sections = data.get("sections", [])

        question_texts = [q[1] if isinstance(q, tuple) and len(q) > 1 else str(q) for q in questions]

        if not test_code or not questions or not answers or not scores:
            await callback.message.reply("🐱 На жаль, дані про тест недоступні. Спробуйте пройти тест знову.")
            return

        test_info = get_test_info(test_code)
        test_name = test_info[0] if test_info and len(test_info) > 0 else "Тест"

        result = process_test_result(test_code, scores, sections)
        result_text = ""
        for section, score, interpretation in result:
            label = f"{section.capitalize()}: {score} балів" if section else f"Загальний бал: {score}"
            result_text += f"{label}\n{interpretation}\n\n"

        wait_message = await callback.message.reply("🐱 Секундочку, генерую PDF-звіт для вас...")

        pdf_buffer = generate_test_pdf(
            callback.from_user.id, test_code, test_name, question_texts, answers, scores, result_text, sections
        )

        if pdf_buffer:
            await wait_message.delete()
            
            # Створюємо BufferedInputFile для aiogram
            pdf_file = types.BufferedInputFile(
                file=pdf_buffer.getvalue(),
                filename=f"test_results_{test_code}_{datetime.now().strftime('%Y%m%d')}.pdf"
            )
            
            await callback.message.answer_document(
                document=pdf_file,
                caption="🐱 Ось результати вашого тесту у форматі PDF. Ви можете показати їх фахівцю або зберегти для себе."
            )
        else:
            await wait_message.edit_text("🐱 На жаль, сталася помилка при створенні PDF. Спробуйте пізніше.")

    except Exception as e:
        logger.error(f"Помилка створення PDF-звіту: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await callback.message.reply("🐱 На жаль, сталася помилка при створенні звіту. Спробуйте пізніше.")
        except:
            pass


def generate_test_pdf(user_id, test_code, test_name, questions, answers, scores, result_text, sections=None):
    try:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        base_dir = os.path.dirname(os.path.abspath(__file__))
        dejavu_path = os.path.join(base_dir, "DejaVuSans.ttf")
        dejavu_bold_path = os.path.join(base_dir, "DejaVuSans-Bold.ttf")

        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', dejavu_path))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', dejavu_bold_path))
            normal_font = 'DejaVuSans'
            bold_font = 'DejaVuSans-Bold'
        except Exception as e:
            logger.warning(f"Не вдалося зареєструвати шрифти DejaVuSans: {e}")
            normal_font = 'Helvetica'
            bold_font = 'Helvetica-Bold'

        c.setFont(bold_font, 16)
        c.drawString(50, height - 50, f"Результати тесту: {test_name}")
        c.setFont(normal_font, 12)
        c.drawString(50, height - 80, f"Дата проходження: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        c.line(50, height - 90, width - 50, height - 90)

        y_position = height - 120
        max_width = width - 120

        for i, (question, answer, score) in enumerate(zip(questions, answers, scores)):
            if y_position < 100:
                c.showPage()
                c.setFont(normal_font, 12)
                y_position = height - 50

            c.setFont(bold_font, 12)
            c.drawString(50, y_position, f"{i + 1}.")
            c.setFont(normal_font, 12)

            words = question.split()
            lines, current_line = [], ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if c.stringWidth(test_line, normal_font, 12) <= max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            text_y = y_position
            for line in lines:
                c.drawString(70, text_y, line)
                text_y -= 15
            y_position = text_y - 5

            c.drawString(70, y_position, f"Відповідь: {answer} (бал: {score})")
            y_position -= 30

        if y_position < 150:
            c.showPage()
            c.setFont(normal_font, 12)
            y_position = height - 50

        c.line(50, y_position - 10, width - 50, y_position - 10)
        y_position -= 30

        c.setFont(bold_font, 14)
        c.drawString(50, y_position, "РЕЗУЛЬТАТИ:")
        y_position -= 30
        c.setFont(normal_font, 12)

        for line in result_text.splitlines():
            if not line.strip():
                continue

            words = line.split()
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if c.stringWidth(test_line, normal_font, 12) <= max_width:
                    current_line = test_line
                else:
                    c.drawString(50, y_position, current_line)
                    y_position -= 20
                    current_line = word
            if current_line:
                c.drawString(50, y_position, current_line)
                y_position -= 20

            if y_position < 50:
                c.showPage()
                c.setFont(normal_font, 12)
                y_position = height - 50

        c.showPage()
        c.setFont(bold_font, 12)
        c.drawString(50, 100, "Розроблено @Neyrovidminni_kotyki_bot")
        c.setFont(normal_font, 12)
        c.drawString(50, 70, "Цей звіт не є діагнозом і має консультативний характер.")
        c.drawString(50, 50, "Рекомендується консультація з фахівцем для інтерпретації результатів.")

        c.save()
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"Помилка генерації PDF: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

router = Router()
router.callback_query.register(pdf_report, F.data == "pdf_report")