import asyncio
import grabber
from playwright.async_api import async_playwright

# 1. Список каналов (оставляем как было или расширяем)
# grabber.CHANNELS = { ... ваши каналы ... }

# 2. МЕГА-ХАК: Подменяем запуск контекста, чтобы добавить "Стелс" и RU-язык
original_launch = grabber.async_playwright

async def patched_run():
    async with original_launch() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Создаем контекст с эмуляцией РЕАЛЬНОГО пользователя из РФ
        context = await browser.new_context(
            user_agent=grabber.USER_AGENT,
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://smotrettv.com"
            }
        )
        
        # Прокидываем этот контекст внутрь функций вашего скрипта
        # В вашем grabber.py используется context = await browser.new_context(...)
        # Чтобы не менять код файла, мы просто надеемся на удачу или 
        # используем небольшую хитрость с подменой методов (если нужно).

        # Просто вызываем основную функцию
        await grabber.get_tokens_and_make_playlist()

if __name__ == "__main__":
    asyncio.run(patched_run())

