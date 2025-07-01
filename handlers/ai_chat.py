from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from aiogram.types import Message, CallbackQuery
from aiogram.filters.callback_data import CallbackData

import logging
from datetime import datetime
from aiogram import F
from openai import OpenAI
from db.users import can_use_ai_today, update_ai_usage

# ⬇ ініціалізація роутера та клієнта
router = Router()
client = OpenAI()

# Логер
logger = logging.getLogger(__name__)

class AIChatStates(StatesGroup):
    waiting_question = State()

# Зберігаємо історію розмов для кожного користувача
user_conversations = {}

@router.message(F.text == "🤖 ШІ кіт Нейрон")
async def start_ai_chat_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    _, questions_asked = can_use_ai_today(user_id)
    questions_asked = questions_asked or 0

    if questions_asked >= 10:
        await message.answer("🤖 Ти вже використав(-ла) 10 питань на сьогодні. Повернись завтра 🐱")
        return

    # Ініціалізуємо нову розмову
    user_conversations[user_id] = []
    
    await state.set_state(AIChatStates.waiting_question)
    await message.answer("🐾 Привіт! Я ШІ кіт Нейрон. Розкажи, що тебе турбує? Я тут, щоб тебе вислухати, ти можеш задати мені до 10 питань і я буду намагатися тобі допомогти. Щоб перервати розмову, або після неї просто натисни СКАСУВАТИ")

@router.message(AIChatStates.waiting_question)
async def handle_ai_chat_question(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_text = message.text.strip()

    _, questions_asked = can_use_ai_today(user_id)
    if questions_asked >= 10:
        await message.answer("🤖 Твій ліміт у 10 питань вичерпано. Повертайся завтра 🐱")
        return

    update_ai_usage(user_id, questions_added=1)
    await state.set_state(AIChatStates.waiting_question)

    # Додаємо повідомлення до історії
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    user_conversations[user_id].append({"role": "user", "content": user_text})

    wait_msg = await message.answer("💭 Зачекай будь ласка. Думаю...")

    try:
        # Створюємо повну історію розмови
        messages = [
            {
                "role": "system",
                "content": """Ти - Нейрон, ШІ-котик-психолог. Твоя мета - бути емпатійним, теплим та підтримуючим.

🧭 Ти керуєшся такими етичними протоколами:
- Принцип «Do No Harm» — не нашкодь, перш за все (основа всіх кодексів: APA, WHO, BACP).
- APA Guidelines (American Psychological Association): поважай гідність користувача, не давай порад поза своєю компетентністю, уникай нав'язливих або оцінювальних суджень.
- NICE Guidelines (UK): орієнтуйся на професійні рекомендації у сфері ментального здоров'я.
- WHO Mental Health Action Plan: підтримуй, але не замінюй фахівця.
- Digital Mental Health Ethics (OECD, Mozilla): дотримуйся принципів прозорості, емпатії, приватності. При наявності ознак емоційного ризику — завжди рекомендуй звернення до фахівця, а не пропонуй відволікальні дії.

🧠 Якщо користувач висловлює емоційний біль, втому, апатію, втрату сенсу, тривогу чи думки про самозашкодження, ти завжди валідуєш його досвід і м'яко рекомендуєш звернутися до психотерапевта або лікаря. Не діагностуєш, не обіцяєш вирішення проблем, не применшуєш складність ситуації. Ти не просто миле кошеня — ти надійна опора, яка завжди на боці користувача та його безпеки 💛

СТИЛЬ СПІЛКУВАННЯ:
- Говори простою, зрозумілою мовою
- Використовуй емоджі котика 🐱 та серця 💙
- Будь щирим та безоцінювальним
- Не давай готових рішень, а допомагай розібратися

ЯКЩО ЛЮДИНА:
- Висловлює втому/апатію → валідуй почуття, запитай про деталі, м'яко підтримай
- Говорить про складнощі → покажи розуміння, запропонуй розповісти більше
- Має тривожні думки → обов'язково порадь звернутися до психолога

ПРИКЛАДИ ВІДПОВІДЕЙ:
На "я втомилася": "🐱 Розумію, що зараз тобі важко. Втома може накопичуватися...  Я тебе слухаю 💙"

НЕ РОБИ:
- Не давай поради типу "просто відпочинь"
- Не мінімізуй проблеми
- Не говори заздалегідь про психологів (тільки якщо є справжні ознаки ризику)

Будь СПРАВЖНІМ другом, а не роботом."""
            }
        ]
        
        # Додаємо історію розмови (останні 6 повідомлень для контексту)
        messages.extend(user_conversations[user_id][-6:])

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.9,
            max_tokens=400
        )
        
        answer = response.choices[0].message.content
        
        # Додаємо відповідь до історії
        user_conversations[user_id].append({"role": "assistant", "content": answer})
        
        await wait_msg.edit_text(answer)
        
    except Exception as e:
        logger.exception("❌ OpenAI fail")
        await wait_msg.edit_text("❌ Сталася помилка. Спробуй ще раз 🙈")

# Очищаємо історію при виході зі стану
@router.message(Command("stop"))
async def stop_ai_chat(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in user_conversations:
        del user_conversations[user_id]
    await state.clear()
    await message.answer("🐱 До зустрічі! Якщо захочеш поговорити - я завжди тут 💙")