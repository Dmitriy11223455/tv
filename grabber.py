import asyncio
import random
from playwright.async_api import async_playwright

CHANNELS = {
    "Первый канал": "https://smotrettv.com/1003-pervyj-kanal.html",
    "Россия 1": "https://smotrettv.com/784-rossija-1.html",
    "Звезда": "https://smotrettv.com/310-zvezda.html",
    "ТНТ": "https://smotrettv.com/329-tnt.html",
    "Россия 24": "https://smotrettv.com/217-rossija-24.html",
    "СТС": "https://smotrettv.com/783-sts.html",
    "НТВ": "https://smotrettv.com/6-ntv.html",
    "Рен ТВ": "https://smotrettv.com/316-ren-tv.html"
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

async def get_tokens_and_make_playlist():
    playlist_streams = [] 

    async with async_playwright() as p:
        print(">>> Запуск браузера...")
        browser = await p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage"
        ])
        
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1280, 'height': 720},
            extra_http_headers={
                "Referer": "https://smotrettv.com",
                "Origin": "https://smotrettv.com"
            }
        )
        
        page = await context.new_page()

        for name, channel_url in CHANNELS.items():
            print(f"[*] Граббинг: {name}...", end=" ", flush=True)
            current_stream_url = None

            # Расширенный перехват: ловим m3u8, токены и любые CDN вещателей
            async def handle_request(request):
                nonlocal current_stream_url
                u = request.url
                if ".m3u8" in u:
                    # Ищем ключевые признаки живого потока
                    if any(key in u for key in ["token=", "mediavitrina", "vittv", "p7live", "v3a1", "master"]):
                        if not current_stream_url:
                            current_stream_url = u

            page.on("request", handle_request)
            
            try:
                # Ожидание networkidle для стабильности на GitHub
                await page.goto(channel_url, wait_until="networkidle", timeout=60000)
                
                # Имитируем активность (скролл и клик)
                await page.mouse.wheel(0, 400)
                await asyncio.sleep(5)
                
                # Кликаем "сильно", чтобы пробить возможные оверлеи
                await page.click("body", position={"x": 640, "y": 360}, force=True)
                await asyncio.sleep(1)
                await page.keyboard.press("Space")
                
                # Ожидание ссылки
                for _ in range(20):
                    if current_stream_url: break
                    await asyncio.sleep(1)

                if current_stream_url:
                    playlist_streams.append((name, current_stream_url))
                    print(f"[OK]")
                else:
                    # Попытка №2 если сразу не поймали
                    await page.mouse.click(640, 360)
                    await asyncio.sleep(5)
                    if current_stream_url:
                        playlist_streams.append((name, current_stream_url))
                        print(f"[OK+]")
                    else:
                        print(f"[FAIL]")

            except Exception as e:
                print(f"[ERROR]")

            page.remove_listener("request", handle_request)
            await asyncio.sleep(random.uniform(2, 5))

        if playlist_streams:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for name, link in playlist_streams: 
                    f.write(f'#EXTINF:-1, {name}\n{link}\n')
            print(f"\n>>> Готово! Собрано: {len(playlist_streams)}/{len(CHANNELS)}")
        else:
            print("\n>>> Ошибка: ссылки не найдены.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())
