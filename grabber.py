import asyncio
import os
import re
import random
from playwright.async_api import async_playwright

# Конфигурация каналов
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

# Единый User-Agent для браузера и плейлиста
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Шаблон ссылки для DRM-Play
# Используем двойные скобки {{ }}, чтобы .format не трогал их раньше времени
STREAM_BASE_URL = "https://server.smotrettv.com/{channel_id}.m3u8?token={token}|Referer=https://smotrettv.com/|User-Agent={ua}"

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        # Запуск браузера с обходом детекции ботов
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        login = os.getenv('LOGIN')
        password = os.getenv('PASSWORD')

        if not login or not password:
            print("ОШИБКА: Не установлены переменные LOGIN и PASSWORD в GitHub Secrets!", flush=True)
            return

        print("Авторизация на smotrettv.com...", flush=True)
        try:
            await page.goto("https://smotrettv.com/", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_selector('input[name="email"]', timeout=30000)
            await page.fill('input[name="email"]', login)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            
            # Ждем завершения редиректа после входа
            await asyncio.sleep(10) 
            print("Успешный вход в аккаунт.", flush=True)
        except Exception as e:
            print(f"Ошибка авторизации: {e}", flush=True)

        playlist_data = "#EXTM3U\n"
        
        for name, channel_url in CHANNELS.items():
            print(f"Обработка: {name}...", flush=True)
            current_token = None

            # Обработчик сетевых запросов для поиска токена
            def handle_request(request):
                nonlocal current_token
                if "token=" in request.url:
                    match = re.search(r'token=([^&]+)', request.url)
                    if match:
                        current_token = match.group(1)

            page.on("request", handle_request)
            
            try:
                # Переход на страницу канала
                await page.goto(channel_url, wait_until="domcontentloaded", timeout=60000)
                
                # Имитация движения мыши для активации плеера
                await page.mouse.move(random.randint(100, 600), random.randint(100, 600))
                
                # Ждем появления токена (сайт делает запрос не сразу)
                await asyncio.sleep(random.randint(18, 25)) 

                if not current_token:
                    print(f"   [-] Токен не пойман. Пробую обновить страницу...", flush=True)
                    await page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(20)

                if current_token:
                    # Чистим ID канала (берем последнее слово из URL)
                    channel_id = channel_url.split("/")[-1].replace(".html", "")
                    
                    # Генерируем ссылку, подставляя ВСЕ параметры, включая UA
                    stream_url = STREAM_BASE_URL.format(
                        channel_id=channel_id, 
                        token=current_token, 
                        ua=USER_AGENT
                    )
                    
                    # Добавляем в плейлист
                    playlist_data += f'#EXTINF:-1, {name}\n'
                    # Дополнительный тег для OTT-плееров
                    playlist_data += f'#EXTVLCOPT:http-referrer=https://smotrettv.com/\n'
                    playlist_data += f'{stream_url}\n'
                    
                    print(f"   [+] Успех: {name} (Token: {current_token[:10]}...)", flush=True)
                else:
                    print(f"   [!] Не удалось получить токен для {name}", flush=True)

                # Пауза между каналами для обхода анти-флуда
                await asyncio.sleep(random.randint(3, 6))

            except Exception as e:
                print(f"Ошибка на канале {name}: {e}", flush=True)

        # Имя файла для GitHub
        filename = "playlist_928374hfkj.m3u"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(playlist_data)
        
        await browser.close()
        print(f"\nОбновление завершено! Файл сохранен: {filename}", flush=True)

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())


