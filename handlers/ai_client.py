from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.users import can_use_ai_today, update_ai_usage
from db.tests import process_test_result
from openai import OpenAI
import logging
from aiogram import Router
from aiogram import F
# ⬇ обовʼязково:
router = Router()

logger = logging.getLogger(__name__)
client = OpenAI()  # Ініціалізуй зі своїм ключем або з config

class AIConsultStates(StatesGroup):
    waiting_question = State()

async def ask_ai_entry(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    user_id = callback.from_user.id
    can_consult, _ = can_use_ai_today(user_id)

    if not can_consult:
        await callback.message.reply("🤖 Ти вже використав(-ла) 1 консультацію на сьогодні. Повернись завтра 🐱")
        return

    # Отримуємо дані з FSM
    data = await state.get_data()
    required_keys = ["test_code", "test_name", "scores", "sections"]
    if not all(k in data for k in required_keys):
        await callback.message.reply("😿 Немає результатів тесту для консультації. Спочатку пройди тест.")
        return

    test_code = data["test_code"]
    test_name = data["test_name"]
    scores = data["scores"]
    sections = data.get("sections", [])

    result = process_test_result(test_code, scores, sections)
    result_text = ""
    for section, score, interpretation in result:
        score = round(score, 1)
        if section:
            result_text += f"{section.capitalize()}: {score} балів\n"
        else:
            result_text += f"Загальний бал: {score} балів\n"
        result_text += f"{interpretation.strip()}\n\n"

    # Зберігаємо дані для AI консультації
    await state.update_data(
        ai_consult_mode=True,
        ai_auto_prompt=(
            f"Я пройшов(-ла) тест {test_name}. Мій результат:\n\n{result_text.strip()}\n"
            f"Поясни, що це означає і як я можу подбати про себе."
        )
    )

    await callback.message.reply(
        f"📊 Твій результат по тесту *{test_name}*:\n\n{result_text.strip()}\n"
        f"🔎 Зараз поясню, що це може означати...",
        parse_mode="Markdown"
    )

    # Автоматично обробляємо запитання
    await process_ai_question_auto(callback.message, state)
    update_ai_usage(user_id, consultations_added=1)

async def process_ai_question_auto(message: types.Message, state: FSMContext):
    """Автоматична обробка запитання на основі результатів тесту"""
    data = await state.get_data()
    
    if not data.get("ai_consult_mode"):
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    test_code = data.get("test_code", "")
    test_name = data.get("test_name", "тест")
    scores = data.get("scores", [])
    sections = data.get("sections", [])

    result = process_test_result(test_code, scores, sections)
    result_text = ""
    for section, score, interpretation in result:
        if section:
            result_text += f"{section.capitalize()}: {score} балів\n"
        else:
            result_text += f"Загальний бал: {score}\n"
        result_text += f"{interpretation.strip()}\n\n"

    user_text = (
        f"Я щойно пройшов(-ла) тест {test_name}.\n"
        f"Ось мій результат:\n\n{result_text.strip()}\n"
        f"Поясни, будь ласка, що це може означати і як краще подбати про себе."
    )

    await _process_ai_request(message.bot, chat_id, user_id, user_text, state)

async def process_ai_question(message: types.Message, state: FSMContext):
    """Обробка запитання користувача"""
    data = await state.get_data()
    
    if not data.get("ai_consult_mode"):
        await message.reply("🤖 Привіт, я котик ШІ Семен 🐾 Напиши запитання.")
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    user_text = message.text.strip()

    await _process_ai_request(message.bot, chat_id, user_id, user_text, state)

async def _process_ai_request(bot, chat_id: int, user_id: int, user_text: str, state: FSMContext):
    """Внутрішня функція для обробки AI запиту"""
    _, questions_asked = can_use_ai_today(user_id)
    questions_asked = questions_asked or 0
    
    if questions_asked >= 10:
        await bot.send_message(chat_id=chat_id, text="🤖 Твій ліміт у 10 питань вичерпано. Повертайся завтра 🐱")
        return

    update_ai_usage(user_id, questions_added=1)
    
    # Оновлюємо лічильник запитань в стані
    await state.update_data(ai_questions=questions_asked + 1)

    wait_msg = await bot.send_message(chat_id=chat_id, text="💬 Думаю над відповіддю...")

    try:
        logger.info("🧠 Запит до OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": (
                    "Ти емпатичний асистент-консультант з психологічною освітою. "
                    "Не ставиш діагнозів. Пояснюєш значення результатів, "
                    "пропонуєш корисні ідеї, підтримуєш. Якщо щось може бути серйозним — "
                    "рекомендуєш звернутись до фахівця. Пишеш мʼяко і турботливо, без оцінок. "
                    "Звертайся на ти, використовуй нейтральні фрази підтримки. Використовуй тільки данні з тестів які пройшов користувач не шукай сторонні"
                )},
                {"role": "user", "content": user_text}
            ],
            temperature=0.7,
            max_tokens=500
        )
        reply = response.choices[0].message.content

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=wait_msg.message_id,
            text=f"🤖 {reply}"
        )

    except Exception as e:
        logger.exception("❌ Помилка при зверненні до OpenAI")
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=wait_msg.message_id,
                text="❌ Сталася помилка з OpenAI. Спробуй пізніше 🙈"
            )
        except:
            await bot.send_message(chat_id=chat_id, text="❌ Сталася помилка з OpenAI.")

router.callback_query.register(ask_ai_entry, F.data == "ask_ai")
router.message.register(process_ai_question, AIConsultStates.waiting_question)