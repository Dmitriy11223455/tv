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
            "--disable-setuid-sandbox"
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
            print(f"[*] Граббинг: {name}...")
            current_stream_url = None

            # Расширенный перехват: ловим m3u8, токены и любые CDN вещателей
            async def handle_request(request):
                nonlocal current_stream_url
                u = request.url
                if ".m3u8" in u:
                    if any(key in u for key in ["token=", "mediavitrina", "vittv", "p7live", "v3a1"]):
                        if not current_stream_url:
                            current_stream_url = u

            context.on("request", handle_request)
            
            try:
                # Увеличиваем таймаут и ждем первичной загрузки
                await page.goto(channel_url, wait_until="domcontentloaded", timeout=90000)
                
                # Имитируем активность человека (движение мыши над плеером)
                await page.mouse.move(640, 360)
                await asyncio.sleep(7)
                
                # Кликаем в центр плеера несколько раз для пробития баннеров
                for _ in range(2):
                    await page.mouse.click(640, 360)
                    await asyncio.sleep(1)
                
                await page.keyboard.press("Space")
                
                # Даем время на прогрузку рекламы и самого потока
                for _ in range(25):
                    if current_stream_url: break
                    await asyncio.sleep(1)

                if current_stream_url:
                    playlist_streams.append((name, current_stream_url))
                    print(f"   [OK] {name} пойман")
                else:
                    # Последняя попытка: если ссылка не поймана, пробуем еще один клик
                    await page.mouse.click(600, 300)
                    await asyncio.sleep(5)
                    if current_stream_url:
                        playlist_streams.append((name, current_stream_url))
                        print(f"   [OK] {name} пойман после доп. клика")
                    else:
                        print(f"   [!] {name} не найден")

            except Exception as e:
                print(f"   [!] Ошибка на {name}: {e}")

            context.remove_listener("request", handle_request)
            # Пауза между каналами, чтобы не триггерить защиту
            await asyncio.sleep(random.uniform(5, 10))

        # Запись результата
        if playlist_streams:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for name, link in playlist_streams: 
                    f.write(f'#EXTINF:-1, {name}\n{link}\n')
            print(f"\n>>> Готово! Собрано каналов: {len(playlist_streams)} из {len(CHANNELS)}")
        else:
            print("\n>>> Ошибка: ссылки не найдены.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())
