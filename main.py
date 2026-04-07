#!/usr/bin/env python3
"""
Deal Post Bot v6 — Modular entry point.
Render-compatible: runs a tiny aiohttp health-check server on $PORT
alongside the Telegram polling loop.
"""
import os
import asyncio
import logging
from aiohttp import web

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import BOT_TOKEN, log
from modules.bot_handlers import cmd_start, handle_message


# ── Health-check server (required by Render free tier) ───────────────────────

async def _health(request):
    return web.Response(text="OK")


async def _run_health_server():
    port = int(os.environ.get("PORT", 8080))
    app  = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info(f"Health-check server listening on port {port}")
    # Keep running forever alongside the bot
    while True:
        await asyncio.sleep(3600)


# ── Bot setup ─────────────────────────────────────────────────────────────────

async def _run_bot():
    if BOT_TOKEN == "YOUR_TOKEN":
        raise ValueError("Set TELEGRAM_BOT_TOKEN environment variable!")

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(
        MessageHandler(
            (filters.TEXT | filters.CAPTION) & ~filters.COMMAND,
            handle_message,
        )
    )

    log.info("DealBot v6 starting (polling)...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    log.info("DealBot v6 running.")
    # Keep alive until cancelled
    while True:
        await asyncio.sleep(3600)


# ── Main: run both concurrently ───────────────────────────────────────────────

async def _main():
    await asyncio.gather(
        _run_health_server(),
        _run_bot(),
    )


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
