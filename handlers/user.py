import logging
import traceback
import io
from io import BytesIO
from aiogram import types, Router, F
from aiogram.types import ReplyKeyboardMarkup, InputFile, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from states import RegistrationForm, ApplicationForm
from bot import dp, bot
from db import get_db_pool  # ✅ Получаем функцию для доступа к пулу

# Настройка логирования
logger = logging.getLogger(__name__)

# ✅ Главная клавиатура
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Информация. Кто мы?🪴")],
        [KeyboardButton(text="Личный кабинет👨🏻‍💻")],
        [KeyboardButton(text="Перейти на веб-приложение🖥️")],
        [KeyboardButton(text="Помощь🤝")],
        [KeyboardButton(text="🗑 Удалить меня")],
    ],
    resize_keyboard=True
)

# ✅ Роутер
router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await message.answer("🌿 Добро пожаловать! Выберите действие:", reply_markup=keyboard)


@router.message(F.text.lower() == "информация. кто мы?🪴")
async def send_info(message: types.Message):
    info_text = (
        "🌍 **Защитник природы** – это сервис для очистки загрязнённых мест.\n\n"
        "Здесь вы можете:\n"
        "● Узнать об экологии\n"
        "● Присоединиться к эко-движению\n"
        "● Найти полезные ресурсы\n\n"
        "💚 Вместе сделаем мир чище!"
    )
    await message.answer(info_text, parse_mode="Markdown")


@router.message(F.text.lower() == "📝 регистрация")
async def start_registration(message: types.Message, state: FSMContext):
    await message.answer("✉️ Введите ваш email.")
    await state.set_state(RegistrationForm.email)


@router.message(RegistrationForm.email, F.text)
async def save_user_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if "@" not in email or "." not in email:
        await message.answer("❌ Некорректный email. Введите правильный email.")
        return

    user_id = message.from_user.id
    db_pool = get_db_pool()
    if db_pool is None:
        await message.answer("❌ База данных не инициализирована. Попробуйте позже.")
        return

    async with db_pool.acquire() as conn:
        try:
            async with conn.transaction():
                # Проверяем: есть ли пользователь по Telegram ID
                existing_by_id = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

                # Проверяем: есть ли пользователь по email (например, если зарегистрировался через сайт)
                existing_by_email = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)

                if existing_by_id:
                    await message.answer("✅ Вы уже зарегистрированы в боте!")
                    await state.clear()
                    return

                if existing_by_email:
                    # Привязываем Telegram ID к веб-учетке
                    await conn.execute(
                        "UPDATE users SET id = $1 WHERE email = $2", user_id, email
                    )
                    await message.answer("✅ Вы успешно вошли — Telegram-аккаунт привязан к веб-профилю!", reply_markup=keyboard)
                else:
                    # Новый пользователь
                    await conn.execute("""
                        INSERT INTO users (id, email, password_hash, first_name)
                        VALUES ($1, $2, $3, $4)
                    """, user_id, email, 'default', 'default')
                    await message.answer("✅ Регистрация прошла успешно!", reply_markup=keyboard)

                await state.clear()

        except Exception as e:
            logger.error(f"❌ Ошибка регистрации: {e}\n{traceback.format_exc()}")
            await message.answer("❌ Произошла ошибка. Попробуйте снова.")


@router.message(F.text.lower() == "личный кабинет👨🏻‍💻")
async def user_profile(message: types.Message):
    user_id = message.from_user.id
    db_pool = get_db_pool()
    if db_pool is None:
        await message.answer("❌ База данных не инициализирована. Попробуйте позже.")
        return

    async with db_pool.acquire() as conn:
        try:
            user_data = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

            if not user_data:
                register_keyboard = ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="📝 Регистрация")]],
                    resize_keyboard=True
                )
                await message.answer("❌ Вы не зарегистрированы.", reply_markup=register_keyboard)
                return

            application_count = await conn.fetchval(
                "SELECT COUNT(*) FROM applications WHERE user_id = $1", user_id
            )

            coins = user_data.get("coins", 0)


            profile_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📌 Взять задание", callback_data="take_task")],
                    [InlineKeyboardButton(text="🖼 Оставить заявку", callback_data="submit_application")],
                    [InlineKeyboardButton(text="🗑 удалить меня", callback_data="delete_user")]
                ]
            )

            # Определяем источник регистрации
            via_bot = user_data["id"] is not None
            via_web = user_data["email"] and user_data["password_hash"] and user_data["password_hash"] != "default"

            if via_bot and via_web:
                origin = "📱 Бот и 🌐 Веб"
            elif via_bot:
                origin = "📱 Только бот"
            elif via_web:
                origin = "🌐 Только веб"
            else:
                origin = "❓ Неопределено"

            text = (
                f"🆔 Ваш ID: {user_data['id']}\n"
                f"👤 Логин: {message.from_user.username or 'Не указан'}\n"
                f"📧 Email: {user_data['email'] or '—'}\n"
                f"📋 Ваши заявки: {application_count}\n"
                f"💰 Монеты: {coins}\n"
                f"🛡 Регистрация через: {origin}"
            )
            await message.answer(text, reply_markup=profile_keyboard)

        except Exception as e:
            logger.exception("❌ Ошибка при загрузке профиля пользователя")
            await message.answer("❌ Произошла ошибка. Попробуйте снова.")


@router.callback_query(lambda c: c.data == "submit_application")
async def application_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📸 Отправьте фото загрязненного участка.")
    await state.set_state(ApplicationForm.photo)


@router.message(ApplicationForm.photo, F.photo)
async def save_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(photo=file_id)
    await message.answer("📝 Теперь отправьте описание загрязненного участка.")
    await state.set_state(ApplicationForm.description)


@router.message(ApplicationForm.description, F.text)
async def save_description(message: types.Message, state: FSMContext):
    description = message.text.strip()
    if not description:
        await message.answer("❗ Описание не может быть пустым. Введите описание.")
        return

    await state.update_data(description=description)
    await message.answer("📍 Отправьте местоположение.")
    await state.set_state(ApplicationForm.location)


@router.message(ApplicationForm.location, F.location)
async def save_location(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    latitude, longitude = message.location.latitude, message.location.longitude
    description, photo = data.get("description"), data.get("photo")

    db_pool = get_db_pool()
    if db_pool is None:
        await message.answer("❌ База данных не инициализирована. Попробуйте позже.")
        return

    async with db_pool.acquire() as conn:
        try:
            async with conn.transaction():
                photo_bytes = photo.encode("utf-8")
                await conn.execute(
                    """
                    INSERT INTO applications (user_id, location, description, photo)
                    VALUES ($1, ST_SetSRID(ST_MakePoint($2, $3), 4326), $4, $5)
                    """,
                    user_id, longitude, latitude, description, photo_bytes
                    )



            await message.answer("✅ Заявка успешно отправлена!")
            await state.clear()

        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении заявки: {e}\n{traceback.format_exc()}")
            await message.answer("❌ Произошла ошибка. Попробуйте снова.")


@router.message(F.text.lower() == "🗑 удалить меня")
async def delete_user(message: types.Message):
    user_id = message.from_user.id

    db_pool = get_db_pool()
    if db_pool is None:
        await message.answer("❌ База данных не инициализирована. Попробуйте позже.")
        return

    async with db_pool.acquire() as conn:
        try:
            await conn.execute("DELETE FROM applications WHERE user_id = $1", user_id)
            result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)

            if result == "DELETE 0":
                await message.answer("❌ Вы не зарегистрированы.")
            else:
                await message.answer("✅ Ваш аккаунт удалён.")

        except Exception as e:
            logger.error(f"❌ Ошибка при удалении пользователя: {e}\n{traceback.format_exc()}")
            await message.answer("❌ Ошибка. Попробуйте снова.")





@router.callback_query(lambda c: c.data == "delete_user")
async def delete_user_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    db_pool = get_db_pool()
    if db_pool is None:
        await callback.message.answer("❌ База данных не инициализирована. Попробуйте позже.")
        return

    async with db_pool.acquire() as conn:
        try:
            await conn.execute("DELETE FROM applications WHERE user_id = $1", user_id)
            result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)

            if result == "DELETE 0":
                await callback.message.answer("❌ Вы не зарегистрированы.")
            else:
                await callback.message.answer("✅ Ваш аккаунт удалён.")

        except Exception as e:
            logger.error(f"❌ Ошибка при удалении пользователя (callback): {e}\n{traceback.format_exc()}")
            await callback.message.answer("❌ Ошибка. Попробуйте снова.")

@router.callback_query(lambda c: c.data == "take_task")
async def show_random_task(callback: types.CallbackQuery):
    db_pool = get_db_pool()
    if db_pool is None:
        await callback.message.answer("❌ База данных не инициализирована.")
        return

    async with db_pool.acquire() as conn:
        task = await conn.fetchrow("""
            SELECT id, description, photo, ST_AsText(location) AS location
            FROM applications
            ORDER BY RANDOM()
            LIMIT 1
        """)

        if not task:
            await callback.message.answer("❌ Задания отсутствуют.")
            return

        # Описание
        description = task["description"]

        # Попробуем отправить фото
        try:
            photo_bytes = task["photo"]
            photo_file = InputFile(io.BytesIO(photo_bytes), filename="photo.jpg")
            caption_text = f"📄 *Описание:*\n{description}"
            await callback.message.answer_photo(photo_file, caption=caption_text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отправить фото: {e}")
            await callback.message.answer(f"📄 *Описание:*\n{description}", parse_mode="Markdown")

        # Местоположение
        try:
            coords = task["location"].replace("POINT(", "").replace(")", "").split()
            longitude, latitude = map(float, coords)
            await callback.message.answer_location(latitude=latitude, longitude=longitude)
            await callback.message.answer("📍 *Местоположение:* отмечено на карте.", parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось распарсить координаты: {e}")

        # Кнопки
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Другое задание", callback_data="take_task")],
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
            ]
        )
        await callback.message.answer("Выберите действие:", reply_markup=keyboard)



@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
            await callback.message.answer("🌿 Добро пожаловать! Выберите действие:", reply_markup=keyboard)



# ✅ Регистрация обработчиков
def setup_user(dp):
    dp.include_router(router)
    dp.message.register(start_handler, Command('start'))
    dp.message.register(send_info, lambda message: (message.text or "").lower() == "информация. кто мы?🪴")
    dp.message.register(user_profile, lambda message: (message.text or "").lower() == "личный кабинет👨🏻‍💻")
    dp.message.register(delete_user, lambda message: (message.text or "").lower() == "🗑 удалить меня")
    dp.message.register(start_registration, lambda message: (message.text or "").lower() == "📝 регистрация")
    dp.callback_query.register(show_random_task, lambda c: c.data == "take_task")
    dp.callback_query.register(back_to_menu, lambda c: c.data == "back_to_menu")



    dp.message.register(save_user_email, RegistrationForm.email)
    dp.callback_query.register(delete_user_callback, lambda c: c.data == "delete_user")



