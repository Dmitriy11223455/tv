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

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
STREAM_BASE_URL = "https://server.smotrettv.com/{channel_id}.m3u8?token={token}|Referer=https://smotrettv.com/|User-Agent={ua}"

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(user_agent=USER_AGENT, viewport={'width': 1280, 'height': 720})
        page = await context.new_page()

        login = os.getenv('LOGIN')
        password = os.getenv('PASSWORD')

        print("Авторизация...", flush=True)
        try:
            await page.goto("https://smotrettv.com/", wait_until="commit", timeout=60000)
            await page.fill('input[name="email"]', login)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            await asyncio.sleep(10) 
        except Exception as e:
            print(f"Ошибка входа: {e}", flush=True)

        playlist_data = "#EXTM3U\n"
        
        for name, channel_url in CHANNELS.items():
            print(f"Обработка: {name}...", flush=True)
            current_token = None

            async def handle_request(request):
                nonlocal current_token
                # Ищем токен в любом запросе к серверу вещания
                if "server.smotrettv.com" in request.url and "token=" in request.url:
                    match = re.search(r'token=([^&|\s]+)', request.url)
                    if match:
                        current_token = match.group(1)

            page.on("request", handle_request)
            
            try:
                await page.goto(channel_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(5)

                # Попытка кликнуть по плееру, чтобы вызвать запрос токена
                try:
                    # Убираем возможные баннеры/оверлеи
                    await page.evaluate('() => document.querySelectorAll(".ads, .overlay").forEach(el => el.remove())')
                    # Кликаем в центр области плеера
                    await page.mouse.click(640, 360) 
                    print(f"   [*] Клик по плееру выполнен", flush=True)
                except:
                    pass

                # Ждем токен (увеличено время)
                for _ in range(30):
                    if current_token: break
                    await asyncio.sleep(1)

                if current_token:
                    channel_id = channel_url.split("/")[-1].replace(".html", "")
                    stream_url = STREAM_BASE_URL.format(channel_id=channel_id, token=current_token, ua=USER_AGENT)
                    playlist_data += f'#EXTINF:-1, {name}\n#EXTVLCOPT:http-referrer=https://smotrettv.com/\n{stream_url}\n'
                    print(f"   [+] Токен получен: {current_token[:15]}...", flush=True)
                else:
                    print(f"   [!] Токен НЕ найден", flush=True)

                await asyncio.sleep(random.randint(3, 5))

            except Exception as e:
                print(f"Ошибка: {e}", flush=True)

        with open("playlist_928374hfkj.m3u", "w", encoding="utf-8") as f:
            f.write(playlist_data)
        
        await browser.close()
        print("\nГотово!", flush=True)

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())
