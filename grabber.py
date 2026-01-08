import asyncio
import os
import re
import random
from playwright.async_api import async_playwright

# --- ВАШИ ДАННЫЕ ДЛЯ ВХОДА ---
MY_LOGIN = "ВАШ_ЛОГИН"
MY_PASSWORD = "ВАШ_ПАРОЛЬ"

# --- ВАШИ НАСТРОЙКИ ---
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
        print(">>> Запуск браузера Chrome...")
        # Используем 'channel="chrome"', чтобы не скачивать браузеры playwright на забитый диск
        try:
            browser = await p.chromium.launch(
                headless=False, 
                channel="chrome", 
                args=["--disable-blink-features=AutomationControlled"]
            )
        except Exception as e:
            print(f"!!! Ошибка при запуске Chrome: {e}. Пробуем Edge...")
            browser = await p.chromium.launch(headless=False, channel="msedge")
        
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        print(f">>> Авторизация: {MY_LOGIN}...")
        try:
            await page.goto("https://smotrettv.com", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            
            # Ожидание и заполнение полей
            await page.wait_for_selector('input[name="email"]', timeout=15000)
            await page.fill('input[name="email"]', MY_LOGIN)
            await page.fill('input[name="password"]', MY_PASSWORD)
            await page.click('button[type="submit"]')
            
            print(">>> Ждем 10 секунд после клика...")
            await asyncio.sleep(10) 
        except Exception as e:
            print(f">>> Ошибка входа: {e}")

        playlist_data = "#EXTM3U\n"
        
        for name, channel_url in CHANNELS.items():
            print(f"[*] Граббинг канала: {name}...")
            current_token = None

            def handle_request(request):
                nonlocal current_token
                # Ищем токен в сетевых запросах
                if "token=" in request.url:
                    match = re.search(r'token=([^&|\s]+)', request.url)
                    if match:
                        current_token = match.group(1)

            page.on("request", handle_request)
            
            try:
                await page.goto(channel_url, wait_until="commit", timeout=60000)
                await asyncio.sleep(8)

                # Клик по плееру
                await page.mouse.click(640, 360)
                
                # Ждем токен 20 секунд
                for _ in range(20):
                    if current_token:
                        break
                    await asyncio.sleep(1)

                if current_token:
                    channel_id = channel_url.split("/")[-1].replace(".html", "")
                    stream_url = STREAM_BASE_URL.format(channel_id=channel_id, token=current_token, ua=USER_AGENT)
                    playlist_data += f'#EXTINF:-1, {name}\n#EXTVLCOPT:http-referrer=https://smotrettv.com/\n{stream_url}\n'
                    print(f"   [+] Токен найден: {current_token[:15]}...")
                else:
                    print(f"   [!] Токен не найден.")

                await asyncio.sleep(random.randint(2, 4))
            except Exception as e:
                print(f"   [!] Ошибка на канале {name}: {e}")

        # Сохраняем в файл
        with open("playlist_tv.m3u", "w", encoding="utf-8") as f:
            f.write(playlist_data)
        
        await browser.close()
        print(f"\n>>> Работа завершена. Файл сохранен: {os.path.abspath('playlist_tv.m3u')}")

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())

