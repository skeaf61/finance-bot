import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Сначала загружаем окружение
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ Токен не найден в .env файле!")

# Импортируем инициализатор БД и роутеры
from database.db import init_db
from handlers import all_handlers_router

async def set_main_menu(bot: Bot):
    main_menu_commands = [
        types.BotCommand(command="/start", description="🤖 Главное меню"),
        types.BotCommand(command="/expense", description="📉 Записать расход"),
        types.BotCommand(command="/income", description="💰 Записать доход"),
        types.BotCommand(command="/stats", description="📊 Статистика за месяц"),
        types.BotCommand(command="/delete_by_id", description="🔍 Удалить расход по номеру операции"),
        types.BotCommand(command="/cancel", description="❌ Отмена действия")
    ]
    await bot.set_my_commands(main_menu_commands)

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Инициализируем базу данных
    init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Подключаем роутер, который объединяет в себе все хендлеры
    dp.include_router(all_handlers_router)
    
    await set_main_menu(bot)
    
    print("🚀 Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())