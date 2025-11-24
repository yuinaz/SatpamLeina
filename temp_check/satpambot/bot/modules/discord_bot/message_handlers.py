async def handle_on_message(bot, message):
    try:
        from .handlers.invite_guard import check_nsfw_invites
        await check_nsfw_invites(message, bot)
    except Exception:
        pass
    try:
        from .handlers.url_guard import handle_urls
        await handle_urls(message, bot)
    except Exception:
        pass
    try:
        from .handlers.image_handler import handle_image_message
        await handle_image_message(message, bot)
    except Exception:
        pass
    try:
        from .handlers.ocr_handler import handle_ocr_check
        await handle_ocr_check(message, bot)
    except Exception:
        pass
