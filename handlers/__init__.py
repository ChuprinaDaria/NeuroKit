from aiogram import Dispatcher

from .start_phone_main import router as start_router
from .tests_logic import router as test_router
from .share_friend import router as share_router
from .donate import router as donate_router
from handlers.admin import router as admin_router
from .about import router as about_router
from handlers.share_friend import router as share_router
from handlers.pdf import router as pdf_router
from handlers import ai_chat  # або відносний імпорт
from handlers.ai_client import router as ai_router
from handlers.ai_chat import router as ai_chat_router
from handlers import feedback
from . import help 
try:
    from db.phrases import router as support_router
except ImportError:
    support_router = None


def register_all_handlers(dp: Dispatcher):
    dp.include_router(start_router)
    dp.include_router(test_router)
    dp.include_router(share_router)
    dp.include_router(donate_router)
    dp.include_router(admin_router)
    dp.include_router(about_router)
    dp.include_router(pdf_router)
    dp.include_router(ai_chat_router)
    dp.include_router(feedback.router)
    dp.include_router(help.router)
    if ai_router:
        dp.include_router(ai_router)

    if support_router:
        dp.include_router(support_router)
