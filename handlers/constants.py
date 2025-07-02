from enum import IntEnum
from aiogram.fsm.state import StatesGroup, State

class States(IntEnum):
    START = 0
    PHONE = 1
    TEST_MENU = 2
    TEST_IN_PROGRESS = 3
    WAITING_FOR_USERNAME = 5

AI_CONSULT = 10

class FSMStates(StatesGroup):
    START = State()
    PHONE = State()
    TEST_MENU = State()
    ADMIN_MESSAGE = State()
