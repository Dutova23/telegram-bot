from aiogram.fsm.state import StatesGroup, State

# Класс для регистрации пользователя
class RegistrationForm(StatesGroup):
    email = State()  # Ожидаем ввод email

# Класс для работы с задачами
class TaskForm(StatesGroup):
    task_id = State()  # Ожидаем выбор задания
    task_photo = State()  # Ожидаем загрузку фотографии задачи

class ApplicationForm(StatesGroup):
    photo = State()
    description = State()
    email = State()
    location = State()