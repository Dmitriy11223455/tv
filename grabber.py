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
        print(">>> Запуск Edge в виртуальном окне...")
        browser = await p.chromium.launch(
            channel="msedge",
            headless=False, # xvfb на GitHub сделает его виртуально "видимым"
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        
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

            async def handle_request(request):
                nonlocal current_stream_url
                u = request.url
                if ".m3u8" in u:
                    if any(key in u for key in ["token=", "mediavitrina", "vittv", "p7live", "v3a1", "m3u8"]):
                        if not current_stream_url:
                            current_stream_url = u

            page.on("request", handle_request)
            
            try:
                # networkidle помогает дождаться загрузки скриптов плеера
                await page.goto(channel_url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(5)
                
                # Кликаем для активации
                await page.mouse.click(640, 360)
                await page.keyboard.press("Space")
                
                for _ in range(15):
                    if current_stream_url: break
                    await asyncio.sleep(1)

                if current_stream_url:
                    playlist_streams.append((name, current_stream_url))
                    print("[OK]")
                else:
                    print("[FAIL]")

            except Exception as e:
                print(f"[ERR] {e}")

            page.remove_listener("request", handle_request)
            await asyncio.sleep(random.uniform(1, 3))

        if playlist_streams:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for name, link in playlist_streams: 
                    f.write(f'#EXTINF:-1, {name}\n{link}\n')
            print(f"\n>>> Готово! Собрано: {len(playlist_streams)}/{len(CHANNELS)}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())


