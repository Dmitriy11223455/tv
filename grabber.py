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

# Базовый URL теперь включает конструкцию для проброса заголовка Referer
STREAM_BASE_URL = "https://server.smotrettv.com/{channel_id}.m3u8?token={token}|Referer=https://smotrettv.com/|User-Agent={UA}"

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        login = os.getenv('LOGIN')
        password = os.getenv('PASSWORD')

        print("Авторизация на smotrettv.com...", flush=True)
        try:
            await page.goto("https://smotrettv.com/", wait_until="domcontentloaded", timeout=60000)
            # Ожидаем появления полей (на случай медленной загрузки)
            await page.wait_for_selector('input[name="email"]')
            await page.fill('input[name="email"]', login)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            await asyncio.sleep(8) 
            print("Вход выполнен.", flush=True)
        except Exception as e:
            print(f"Ошибка входа: {e}", flush=True)

        playlist_data = "#EXTM3U\n"
        
        for name, channel_url in CHANNELS.items():
            print(f"Парсинг: {name}...", flush=True)
            current_token = None

            def handle_request(request):
                nonlocal current_token
                if "token=" in request.url:
                    match = re.search(r'token=([^&]+)', request.url)
                    if match:
                        current_token = match.group(1)

            page.on("request", handle_request)
            
            try:
                await page.goto(channel_url, wait_until="domcontentloaded", timeout=60000)
                await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                
                # Ожидание появления токена в сетевых запросах
                await asyncio.sleep(random.randint(15, 20)) 

                if not current_token:
                    print(f"   [-] Токен не найден, обновляем...", flush=True)
                    await page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(15)

                if current_token:
                    # Извлекаем ID канала из ссылки (например, 1003-pervyj-kanal)
                    channel_id = channel_url.split("/")[-1].replace(".html", "")
                    
                    # Формируем итоговую ссылку с токеном и Referer
                    stream_url = STREAM_BASE_URL.format(channel_id=channel_id, token=current_token)
                    
                    # Запись в формате, который DRM-Play и OTT-плееры понимают лучше всего
                    playlist_data += f'#EXTINF:-1, {name}\n'
                    playlist_data += f'#EXTVLCOPT:http-referrer=https://smotrettv.com/\n'
                    playlist_data += f'{stream_url}\n'
                    print(f"   [+] Готово: {name}", flush=True)
                else:
                    print(f"   [!] Ошибка: {name} пропущен", flush=True)

                await asyncio.sleep(random.randint(2, 4))

            except Exception as e:
                print(f"Ошибка на канале {name}: {e}", flush=True)

        # Сохранение плейлиста
        filename = "playlist_928374hfkj.m3u"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(playlist_data)
        
        await browser.close()
        print(f"\nПлейлист сохранен в файл: {filename}", flush=True)

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())



