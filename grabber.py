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
MAX_ATTEMPTS = 10  # Лимит попыток для одного канала

async def get_tokens_and_make_playlist():
    playlist_streams = [] 

    async with async_playwright() as p:
        print(">>> Запуск Chrome...")
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(user_agent=USER_AGENT, permissions=["autoplay"])
        page = await context.new_page()

        for name, channel_url in CHANNELS.items():
            print(f"[*] Граббинг: {name}...")
            current_stream_url = None

            async def handle_request(request):
                nonlocal current_stream_url
                u = request.url
                if ".m3u8" in u and not any(x in u for x in ["ads", "telemetree", "analyt"]):
                    current_stream_url = u

            page.on("request", handle_request)
            
            attempt = 0
            while not current_stream_url and attempt < MAX_ATTEMPTS:
                attempt += 1
                try:
                    print(f"    > Попытка {attempt}/{MAX_ATTEMPTS}...")
                    await page.goto(channel_url, wait_until="load", timeout=45000)
                    
                    # Пробиваем плеер
                    await page.mouse.click(640, 360)
                    await asyncio.sleep(2)
                    
                    # Ищем видео во всех фреймах и кликаем
                    for frame in page.frames:
                        try:
                            v = await frame.query_selector("video")
                            if v: await v.click()
                        except: pass

                    # Ждем появления ссылки 15 сек
                    for _ in range(15):
                        if current_stream_url: break
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    print(f"    [!] Ошибка связи: {e}")
                    await asyncio.sleep(2)

            if current_stream_url:
                playlist_streams.append((name, current_stream_url))
                print(f"   [OK] {name} пойман")
            else:
                print(f"   [!] {name} пропущен после {MAX_ATTEMPTS} попыток")

            page.remove_listener("request", handle_request)
            await asyncio.sleep(random.uniform(1, 2))

        if playlist_streams:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for n, l in playlist_streams: 
                    f.write(f'#EXTINF:-1, {n}\n{l}\n')
            print(f"\n>>> Готово! Итого: {len(playlist_streams)} из {len(CHANNELS)}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())
