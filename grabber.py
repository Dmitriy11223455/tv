import asyncio
import datetime
import sys
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def get_all_channels_from_site(page):
    print(">>> [1/3] Загрузка списка каналов...", flush=True)
    try:
        await page.goto("https://smotrettv.com", wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(5)
        found_channels = {}
        links = await page.query_selector_all("a")
        for link in links:
            try:
                url = await link.get_attribute("href")
                name = await link.inner_text()
                if url and name:
                    clean_name = name.split('\n')[0].strip().upper()
                    if len(clean_name) < 2: continue
                    if any(cat in url for cat in ['/public/', '/news/', '/sport/', '/entertainment/']):
                        full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                        if clean_name not in found_channels:
                            found_channels[clean_name] = full_url
                            print(f"    [+] {clean_name}", flush=True)
            except: continue
        return found_channels
    except Exception as e:
        print(f"[!] Ошибка главной: {e}", flush=True)
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> [2/3] Запуск Chromium Stealth...", flush=True)
        browser = await p.chromium.launch(headless=True)
        # Важно: эмулируем реальное устройство
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        CHANNELS = await get_all_channels_from_site(page)
        if not CHANNELS: return

        print(f"\n>>> [3/3] Граббинг токенов (max 20)...", flush=True)
        results = []
        
        for name, url in list(CHANNELS.items())[:20]:
            stream_url = None
            
            # Ловим все m3u8, включая те, что внутри iframe
            async def handle_request(request):
                nonlocal stream_url
                u = request.url
                if ".m3u8" in u and not any(x in u for x in ["yandex", "ads", "log"]):
                    # Mediavitrina или прямые токены
                    if "token=" in u or "master" in u or "index" in u:
                        stream_url = u

            page.on("request", handle_request)
            print(f"[*] {name:.<20}", end=" ", flush=True)

            try:
                await page.goto(url, wait_until="load", timeout=30000)
                await asyncio.sleep(5)
                
                # Ищем кнопку Play или видео во всех фреймах
                found_play = False
                for frame in page.frames:
                    try:
                        play_btn = await frame.query_selector("video, .vjs-play-control, .play")
                        if play_btn:
                            await play_btn.click()
                            found_play = True
                    except: continue
                
                if not found_play:
                    await page.mouse.click(640, 360) # Клик вслепую
                
                # Ждем появления токена до 12 сек
                for _ in range(12):
                    if stream_url: break
                    await asyncio.sleep(1)

                if stream_url:
                    results.append((name, stream_url))
                    print("OK", flush=True)
                else:
                    print("FAIL", flush=True)
            except:
                print("TIME", flush=True)
            
            page.remove_listener("request", handle_request)

        if results:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write(f"# UPDATED: {datetime.datetime.now()}\n")
                for n, l in results:
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> ГОТОВО! Сохранено: {len(results)}", flush=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())












