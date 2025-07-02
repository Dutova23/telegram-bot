from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import db_pool
from config import ADMINS
router = Router()

def is_admin(user_id):
    return user_id in ADMINS



@router.message(F.text.lower() == "проверить отчёты")
async def check_reports(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа!")
        return

    async with db_pool.acquire() as conn:
        task = await conn.fetchrow("SELECT * FROM tasks WHERE status = 'completed' LIMIT 1")

        if not task:
            await message.answer("❌ Нет завершённых заданий для проверки.")
            return

    approve_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{task['id']}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{task['id']}")]
        ]
    )

    await message.answer_photo(
        photo=task["photo"],
        caption=f"📍 Локация: {task['location']}\nОписание: {task['description']}",
        reply_markup=approve_keyboard
    )


async def setup_admin(dp):
    dp.include_router(router)  # Подключаем роутер администратора
