import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import ADMIN_ID
from handlers.selection import router as selection_router


async def on_startup(bot: Bot):
    await bot.send_message(ADMIN_ID, "Бот успешно запущен!")
    logging.info("Бот запущен")


async def on_shutdown(bot: Bot):
    await bot.send_message(ADMIN_ID, "Бот выключается...")
    logging.info("Бот выключается")


async def main():
    bot = Bot(
        token="",
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.include_router(selection_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при работе бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout,
    )

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
