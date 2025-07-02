from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from db import db_pool

router = Router()

class TaskForm(StatesGroup):
    photo = State()
    description = State()
    location = State()

@router.message(F.text.lower() == "📌 взять задание")
async def take_task(message: types.Message):
    user_id = message.from_user.id

    async with db_pool.acquire() as conn:
        task = await conn.fetchrow("SELECT * FROM tasks WHERE status = 'open' LIMIT 1")

        if not task:
            await message.answer("❌ Нет доступных заданий.")
            return

        await conn.execute(
            "UPDATE tasks SET status = 'taken', user_id = $1 WHERE id = $2",
            user_id, task["id"]
        )

        await message.answer(f"✅ Вы взяли задание!\n📍 Локация: {task['location']}")
