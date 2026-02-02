import asyncio
import random
from playwright.async_api import async_playwright

CHANNELS = {
    "Первый канал": "https://smotrettv.comtv/public/1003-pervyj-kanal.html",
    "Россия 1": "https://smotrettv.comtv/public/784-rossija-1.html",
    "Звезда": "https://smotrettv.comtv/public/310-zvezda.html",
    "ТНТ": "https://smotrettv.comtv/entertainment/329-tnt.html",
    "Россия 24": "https://smotrettv.comtv/news/217-rossija-24.html",
    "СТС": "https://smotrettv.comtv/entertainment/783-sts.html",
    "НТВ": "https://smotrettv.comtv/public/6-ntv.html",
    "Рен ТВ": "https://smotrettv.comtv/public/316-ren-tv.html"
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

async def get_tokens_and_make_playlist():
    playlist_streams = [] 

    async with async_playwright() as p:
        print(">>> Запуск браузера...")
        browser = await p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox"
        ])
        
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1280, 'height': 720},
            extra_http_headers={"Referer": "https://smotrettv.com"}
        )
        
        page = await context.new_page()

        for name, channel_url in CHANNELS.items():
            print(f"[*] Граббинг: {name}...")
            current_stream_url = None

            # Глобальный перехватчик (видит запросы из всех фреймов)
            async def handle_request(request):
                nonlocal current_stream_url
                url = request.url
                if ".m3u8" in url and ("token=" in url or "mediavitrina" in url):
                    if not current_stream_url:
                        current_stream_url = url

            context.on("request", handle_request)
            
            try:
                # 1. Переход на страницу
                await page.goto(channel_url, wait_until="load", timeout=60000)
                
                # 2. Ищем фрейм плеера и кликаем в него
                # На smotrettv плеер часто подгружается через iframe
                await asyncio.sleep(5)
                frames = page.frames
                for frame in frames:
                    try:
                        # Пытаемся кликнуть в центре каждого фрейма, чтобы запустить видео
                        await page.mouse.click(640, 360)
                    except:
                        continue

                # 3. Ждем появления ссылки (до 15 секунд)
                for _ in range(15):
                    if current_stream_url: break
                    await asyncio.sleep(1)

                if current_stream_url:
                    playlist_streams.append((name, current_stream_url))
                    print(f"   [OK] Ссылка поймана")
                else:
                    # Если не нашли, пробуем нажать кнопку Play через клавиатуру
                    await page.keyboard.press("Space")
                    await asyncio.sleep(5)
                    if current_stream_url:
                        playlist_streams.append((name, current_stream_url))
                        print(f"   [OK] Ссылка поймана после нажатия Space")
                    else:
                        print(f"   [!] Ссылка не найдена")

            except Exception as e:
                print(f"   [!] Ошибка на {name}: {e}")

            context.remove_listener("request", handle_request)
            await asyncio.sleep(random.uniform(2, 4))

        # Запись результата
        if playlist_streams:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for name, link in playlist_streams: 
                    f.write(f'#EXTINF:-1, {name}\n{link}\n')
            print(f"\n>>> Готово! Собрано каналов: {len(playlist_streams)}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())
