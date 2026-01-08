import asyncio
import os
import re
import random
import json
from playwright.async_api import async_playwright # type: ignore

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
    async with async_playwright() as p:
        print(">>> Запуск браузера с имитацией пользователя...")
        
        # Настройки для обхода детекции ботов на GitHub Actions
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
        
        # Скрываем флаг webdriver
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        login = os.getenv('LOGIN')
        password = os.getenv('PASSWORD')

        print(">>> Переход на главную страницу...", flush=True)
        try:
            await page.goto("https://smotrettv.com", wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(random.uniform(5, 8))
            
            # Пытаемся заполнить форму
            print(">>> Ввод данных авторизации...")
            await page.wait_for_selector('input[name="email"]', timeout=20000)
            await page.fill('input[name="email"]', login)
            await page.fill('input[name="password"]', password)
            
            # Двигаем мышь перед кликом для правдоподобности
            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            await page.click('button[type="submit"]')
            
            await asyncio.sleep(15) 
            print(">>> Авторизация завершена.", flush=True)
        except Exception as e:
            print(f">>> Ошибка при входе (возможно, капча или блок IP): {e}", flush=True)

        playlist_data = "#EXTM3U\n"
        
        for name, channel_url in CHANNELS.items():
            print(f"[*] Граббинг: {name}...", flush=True)
            current_token = None

            def handle_request(request):
                nonlocal current_token
                if "token=" in request.url:
                    match = re.search(r'token=([^&|\s]+)', request.url)
                    if match:
                        current_token = match.group(1)

            page.on("request", handle_request)
            
            try:
                await page.goto(channel_url, wait_until="commit", timeout=60000)
                await asyncio.sleep(10)

                # Клик по плееру
                await page.mouse.click(640, 360)
                
                for _ in range(25):
                    if current_token: break
                    await asyncio.sleep(1)

                if current_token:
                    channel_id = channel_url.split("/")[-1].replace(".html", "")
                    
                    # ФОРМАТ ДЛЯ DRM-PLAY (Заголовки через |)
                    headers = f"|Referer=smotrettv.com{USER_AGENT}"
                    stream_url = f"https://server.smotrettv.com/{channel_id}.m3u8?token={current_token}{headers}"
                    
                    playlist_data += f'#EXTINF:-1, {name}\n{stream_url}\n'
                    print(f"   [+] Токен найден.", flush=True)
                else:
                    print(f"   [!] Токен не пойман.", flush=True)

                await asyncio.sleep(random.uniform(2, 5))

            except Exception as e:
                print(f"   [!] Ошибка на {name}: {e}", flush=True)

        # Сохранение плейлиста
        with open("playlist_928374hfkj.m3u", "w", encoding="utf-8") as f:
            f.write(playlist_data)
        
        await browser.close()
        print("\n>>> Скрипт успешно завершен.", flush=True)

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())



