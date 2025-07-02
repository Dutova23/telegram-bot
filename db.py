import asyncpg

db_pool = None  # глобальный пул

async def init_db():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(
            user='postgres',
            database='PetProjectt',
            host='localhost',
            port=5432  # или другой порт
        )
        print("✅ [db.py] Подключение к базе данных установлено.")


def get_db_pool():
    return db_pool
