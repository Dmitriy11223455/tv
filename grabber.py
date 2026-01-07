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

STREAM_BASE_URL = "htttps://server.smotrettv.com/{channel_id}.m3u8?token={token}"

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        # Настройки для обхода защиты 2026 года
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        login = os.getenv('LOGIN')
        password = os.getenv('PASSWORD')

        print("Логинимся на smotrettv.com...")
        try:
            await page.goto("smotrettv.com", wait_until="networkidle", timeout=60000)
            # Если на сайте есть модальное окно входа, заполняем поля
            await page.fill('input[name="email"]', login)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            await asyncio.sleep(5) 
        except Exception as e:
            print(f"Ошибка при входе: {e}")

        playlist_data = "#EXTM3U\n"
        
        for name, channel_url in CHANNELS.items():
            print(f"Парсим: {name}")
            current_token = None

            def handle_request(request):
                nonlocal current_token
                if "token=" in request.url:
                    match = re.search(r'token=([^&]+)', request.url)
                    if match:
                        current_token = match.group(1)

            page.on("request", handle_request)
            
            try:
                await page.goto(channel_url, wait_until="networkidle", timeout=60000)
                await page.mouse.move(random.randint(10, 100), random.randint(10, 100))
                await asyncio.sleep(15) # Ждем загрузки плеера и токена

                if current_token:
                    channel_id = channel_url.split("/")[-1].replace(".html", "")
                    # ДОБАВЛЯЕМ | В КОНЕЦ. Это заставляет DRM-play игнорировать системный UA
                    stream_url = f"{STREAM_BASE_URL.format(channel_id=channel_id, token=current_token)}|"
                    playlist_data += f'#EXTINF:-1, {name}\n{stream_url}\n'
                    print(f"Успех для {name}")
                else:
                    print(f"Токен для {name} не найден")

            except Exception as e:
                print(f"Ошибка на канале {name}: {e}")

        with open("playlist_928374hfkj.m3u", "w", encoding="utf-8") as f:
            f.write(playlist_data)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())

