import asyncio
import os
import re
from playwright.async_api import async_playwright

# 1. Ссылки теперь точные. 
# Используем регулярное выражение, чтобы вытащить ID (например, '1003-pervyj-kanal')
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

# Шаблон ссылки на поток
STREAM_BASE_URL = "https://server.smotrettv.com/{channel_id}.m3u8?token={token}"

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        login = os.getenv('LOGIN')
        password = os.getenv('PASSWORD')

        print("Переход на сайт для входа...")
        try:
            # На главной часто нужно нажать "Войти", чтобы появились поля
            await page.goto("https://smotrettv.com", wait_until="networkidle", timeout=60000)
            
            # Если полей нет сразу, ищем кнопку входа
            login_button = await page.query_selector('text="Войти", text="Вход"')
            if login_button:
                await login_button.click()
                await asyncio.sleep(2)

            # Ожидаем и заполняем форму
            await page.wait_for_selector('input[name="email"], input[type="email"]', timeout=15000)
            await page.fill('input[name="email"], input[type="email"]', login)
            await page.fill('input[name="password"]', password)
            
            # Клик по кнопке отправки
            await page.click('button[type="submit"]')
            print("Ожидание завершения авторизации...")
            await asyncio.sleep(10) 
        except Exception as e:
            print(f"Предупреждение по авторизации: {e}")

        playlist_data = "#EXTM3U\n"
        
        for name, channel_url in CHANNELS.items():
            print(f"Обработка: {name}...")
            current_token = None

            # Ловим токен в сетевых запросах
            def handle_request(request):
                nonlocal current_token
                if "token=" in request.url:
                    try:
                        # Точный захват токена до следующего амперсанда
                        match = re.search(r'token=([^&]+)', request.url)
                        if match:
                            current_token = match.group(1)
                    except:
                        pass

            page.on("request", handle_request)
            
            try:
                await page.goto(channel_url, wait_until="networkidle", timeout=60000)
                # Ждем прогрузки плеера
                await asyncio.sleep(15) 

                if current_token:
                    # ИСПРАВЛЕНО: Извлекаем ID правильно (убираем .html)
                    # Из '1003-pervyj-kanal.html' получаем '1003-pervyj-kanal'
                    channel_id = channel_url.split("/")[-1].replace(".html", "")
                    
                    stream_url = STREAM_BASE_URL.format(channel_id=channel_id, token=current_token)
                    playlist_data += f'#EXTINF:-1, {name}\n{stream_url}\n'
                    print(f"Успех: Токен получен.")
                else:
                    print(f"Ошибка: Токен не найден для {name}. Возможно, нужен платный аккаунт или плеер не запустился.")

            except Exception as e:
                print(f"Ошибка на {name}: {e}")

        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write(playlist_data)
        
        await browser.close()
        print("\nОбновление завершено. Проверьте файл playlist.m3u")

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())
