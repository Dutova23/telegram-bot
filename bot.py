import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import API_TOKEN
from db import init_db  # Импортируем только функцию для инициализации базы данных
import sys
from handlers import user

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def main():
    # Инициализируем базу данных (внутри db.py это установит db_pool)
    await init_db()

    from db import db_pool  # теперь просто читаем его
    if db_pool is None:
        logging.error("❌ Ошибка: Не удалось подключиться к базе данных!")
        return

    logging.info("✅ База данных подключена!")

    # Регистрируем обработчики
    user.setup_user(dp)

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.critical(f"🚨 Ошибка в боте: {e}", exc_info=True)
    finally:
        await bot.session.close()




# Запуск асинхронной функции
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()  # Для корректной работы внутри асинхронных сред
    asyncio.run(main())  # Здесь вызываем main()
