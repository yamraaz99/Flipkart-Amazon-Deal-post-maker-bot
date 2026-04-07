#!/usr/bin/env python3
"""
Deal Post Bot v6 — Modular entry point.
"""
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import BOT_TOKEN, log
from modules.bot_handlers import cmd_start, handle_message


def main() -> None:
    if BOT_TOKEN == "YOUR_TOKEN":
        raise ValueError("Set TELEGRAM_BOT_TOKEN environment variable!")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.CAPTION) & ~filters.COMMAND,
            handle_message,
        )
    )

    log.info("DealBot v6 running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
