import asyncio
import os
import re
import random
import json
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

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def get_tokens_and_make_playlist():
    # Список будет хранить кортежи: (название_канала, полный_URL_потока)
    playlist_streams = [] 

    async with async_playwright() as p:
        print(">>> Запуск браузера с имитацией пользователя...", flush=True)
        
        # Настройки для обхода детекции ботов и headless режима
        browser = await p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars"
        ])
        
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080},
            locale="ru-RU",
            timezone_id="Europe/Moscow"
        )
        
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # ... (Код авторизации, если нужен, можно вставить здесь, используя os.getenv('LOGIN')/os.getenv('PASSWORD')) ...

        print(">>> Переход по каналам...", flush=True)
        
        for name, channel_url in CHANNELS.items():
            print(f"[*] Граббинг: {name}...", flush=True)
            current_stream_url = None

            # Обработчик запросов, который ловит полный URL с токеном
            def handle_request(request):
                nonlocal current_stream_url
                url = request.url
                if ".m3u8" in url and "token=" in url:
                    current_stream_url = url
                    print(f"   [REQ] Пойман URL: {url}", flush=True)


            page.on("request", handle_request)
            
            try:
                await page.goto(channel_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(random.uniform(5, 8))

                # Клик по плееру (имитация запуска)
                await page.mouse.click(640, 360)
                
                # Ждем 20 секунд, пока URL не будет пойман
                for _ in range(20):
                    if current_stream_url: break
                    await asyncio.sleep(1)

                if current_stream_url:
                    # Добавляем в список кортеж (Название, Полный_URL)
                    playlist_streams.append((name, current_stream_url))
                    print(f"   [+] URL для {name} успешно добавлен в список.", flush=True)
                else:
                    print(f"   [!] URL с токеном для {name} не пойман.", flush=True)

                await asyncio.sleep(random.uniform(2, 5))
                page.remove_listener("request", handle_request)

            except Exception as e:
                print(f"   [!] Ошибка на {name}: {e}", flush=True)

        # Сохранение плейлиста
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for name, link in set(playlist_streams): 
                f.write(f'#EXTINF:-1, {name}\n{link}\n')
        
        await browser.close()
        print(f"\n>>> Скрипт успешно завершен. Файл playlist.m3u создан.", flush=True)

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())

