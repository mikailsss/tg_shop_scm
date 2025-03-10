import asyncio 
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from app.handlers import router
from database.models import async_main

async def main():
    await async_main()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f'Бот выключен\n{e}')
