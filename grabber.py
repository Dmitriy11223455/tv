import asyncio
import os
import re
import random
from playwright.async_api import async_playwright

CHANNELS = {
    "Первый канал": "https://smotrettv.com/tv/public/1003-pervyj-kanal.html",
    "Россия 1": "https://smotrettv.com/tv/public/784-rossija-1.html",
    "Звезда": "https://smotrettv.com/tv/public/310-zvezda.html",
    "ТНТ": "https://smotrettv.com/tv/entertainment/329-tnt.html",
    "Россия 24": "https://smotrettv.com/tv/news/217-rossija-24.html",
    "СТС": "https://smotrettv.com/tv/entertainment/783-sts.html",
    "НТВ": "https://smotrettv.com/tv/public/6-ntv.html",
    "Рен ТВ": "https://smotrettv.com/tv/public/316-ren-tv.html"

}

STREAM_BASE_URL = "https://server.smotrettv.com/{channel_id}.m3u8?token={token}"
USER_AGENT_STRING = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent=USER_AGENT_STRING,
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        login = os.getenv('LOGIN')
        password = os.getenv('PASSWORD')

        print("Переход на сайт для входа...", flush=True)
        try:
            # Используем более универсальные селекторы и таймаут 60 сек
            await page.goto("smotrettv.com", wait_until="domcontentloaded", timeout=60000)
            
            # Проверяем, не появилась ли защита Cloudflare
            if "Just a moment" in await page.title():
                print("Сайт под Cloudflare защитой. Скрипт не пройдет.", flush=True)
                await browser.close()
                return

            # Селекторы, ищущие по типу поля, а не по имени
            await page.wait_for_selector('input[type="email"]', timeout=30000)
            await page.fill('input[type="email"]', login)
            await page.fill('input[type="password"]', password)
            
            await page.click('button[type="submit"]')
            await asyncio.sleep(10) 
            print("Авторизация выполнена.", flush=True)
        except Exception as e:
            print(f"Критическая ошибка авторизации: {e}", flush=True)
            await browser.close() # Прерываем выполнение, так как без входа токены не получить
            return

        playlist_data = "#EXTM3U\n"
        
        for name, channel_url in CHANNELS.items():
            # ... (остальной код для обработки каналов остается прежним) ...
            print(f"Обработка: {name}...", flush=True)
            current_token = None

            def handle_request(request):
                nonlocal current_token
                if "token=" in request.url and "m3u8" in request.url:
                    match = re.search(r'token=([^&]+)', request.url)
                    if match:
                        current_token = match.group(1)

            page.on("request", handle_request)
            
            try:
                await page.goto(channel_url, wait_until="domcontentloaded", timeout=60000)
                await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                await asyncio.sleep(random.randint(15, 22)) 

                if current_token:
                    channel_id = channel_url.split("/")[-1].replace(".html", "")
                    stream_url = STREAM_BASE_URL.format(channel_id=channel_id, token=current_token)
                    playlist_data += f'#EXTINF:-1, {name}\n'
                    playlist_data += f'#KODIPROP:inputstream.adaptive.license_type=widevine\n'
                    playlist_data += f'#EXTVLCOPT:http-user-agent={USER_AGENT_STRING}\n'
                    playlist_data += f'{stream_url}\n'
                    print(f"   [+] Успех: {name}", flush=True)
                else:
                    print(f"   [-] Токен не найден. Пробую обновить страницу...", flush=True)
                    await page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(15)
                    if current_token:
                        channel_id = channel_url.split("/")[-1].replace(".html", "")
                        stream_url = STREAM_BASE_URL.format(channel_id=channel_id, token=current_token)
                        playlist_data += f'#EXTINF:-1, {name}\n'
                        playlist_data += f'#KODIPROP:inputstream.adaptive.license_type=widevine\n'
                        playlist_data += f'#EXTVLCOPT:http-user-agent={USER_AGENT_STRING}\n'
                        playlist_data += f'{stream_url}\n'
                        print(f"   [+] Успех после обновления: {name}", flush=True)
                    else:
                        print(f"   [!] Не удалось получить токен для {name}", flush=True)

                await asyncio.sleep(random.randint(2, 5))

            except Exception as e:
                print(f"Ошибка на {name}: {e}", flush=True)

        with open("playlist_928374hfkj.m3u", "w", encoding="utf-8") as f:
            f.write(playlist_data)
        
        await browser.close()
        print("\nГотово! Все токены обработаны.", flush=True)

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())

