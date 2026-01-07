import asyncio
import os
from playwright.async_api import async_playwright

# 1. КОНФИГУРАЦИЯ (Исправлено: теперь это список ссылок)
CHANNELS = {
    "Первый канал": "smotrettv.com",
    "Россия 1": "smotrettv.com",
    "Звезда": "smotrettv.com",
    "ТНТ": "smotrettv.com",
    "Россия 24": "smotrettv.com",
    "СТС": "smotrettv.com",
    "НТВ": "smotrettv.com",
    "Рен ТВ": "smotrettv.com"
}

STREAM_BASE_URL = "server.smotrettv.com{channel_id}.m3u8?token={token}"

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        # Запуск с дополнительными аргументами для обхода защиты
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        
        # Создаем контекст с реальным User-Agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        login = os.getenv('LOGIN')
        password = os.getenv('PASSWORD')

        print("Попытка входа на сайт...")
        try:
            # Увеличиваем таймаут и ждем готовности сети
            await page.goto("https://smotrettv.com/login", wait_until="domcontentloaded", timeout=60000)
            await page.fill('input[name="email"]', login)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            # Ждем появления элемента, подтверждающего вход (например, кнопка профиля или задержка)
            await asyncio.sleep(10) 
            print("Авторизация выполнена (вероятно).")
        except Exception as e:
            print(f"Ошибка авторизации: {e}")

        playlist_data = "#EXTM3U\n"
        
        for name, channel_url in CHANNELS.items():
            print(f"Обработка: {name}...")
            current_token = None

            # Функция перехвата токена
            def handle_request(request):
                nonlocal current_token
                if "token=" in request.url:
                    try:
                        # Извлекаем только значение токена
                        current_token = request.url.split("token=")[1].split("&")[0]
                    except:
                        pass

            page.on("request", handle_request)
            
            try:
                # Переходим на страницу канала
                await page.goto(channel_url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(10) # Даем время на загрузку плеера и генерацию токена

                if current_token:
                    channel_id = channel_url.split("/")[-1]
                    stream_url = STREAM_BASE_URL.format(channel_id=channel_id, token=current_token)
                    playlist_data += f'#EXTINF:-1, {name}\n{stream_url}\n'
                    print(f"Успех: Токен для {name} получен.")
                else:
                    print(f"Предупреждение: Токен для {name} не найден в трафике.")

            except Exception as e:
                print(f"Ошибка на {name}: {e}")

        # Сохранение файла
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write(playlist_data)
        
        print("\nОбновление завершено. Файл playlist.m3u создан.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())
