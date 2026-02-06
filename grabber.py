import asyncio
import datetime
import sys
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def get_all_channels_from_site(page):
    print(">>> [1/3] Поиск списка каналов...", flush=True)
    try:
        await page.goto("https://smotrettv.com", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)
        found_channels = {}
        links = await page.query_selector_all("a[href*='/']")
        for link in links:
            try:
                url = await link.get_attribute("href")
                name = await link.inner_text()
                if url and name:
                    clean_name = name.strip().split('\n')[0].upper()
                    if len(clean_name) > 1 and any(cat in url for cat in ['/public/', '/news/', '/sport/', '/entertainment/']):
                        full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                        if clean_name not in found_channels:
                            found_channels[clean_name] = full_url
            except: continue
        return found_channels
    except Exception as e:
        print(f"[!] Ошибка главной: {e}", flush=True)
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> [2/3] Запуск браузера...", flush=True)
        # Запуск с отключением флага автоматизации
        browser = await p.chromium.launch(headless=True, args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox'
        ])
        
        init_context = await browser.new_context(user_agent=USER_AGENT)
        temp_page = await init_context.new_page()
        CHANNELS = await get_all_channels_from_site(temp_page)
        await init_context.close()

        if not CHANNELS: 
            print("Каналы не найдены")
            return await browser.close()

        print(f"\n>>> [3/3] Сбор ссылок (изоляция + имитация клика)...", flush=True)
        results = []
        
        for name, url in list(CHANNELS.items())[:15]:
            # Создаем новый контекст для каждого канала, чтобы не было дублей
            context = await browser.new_context(user_agent=USER_AGENT)
            # Скрываем автоматизацию через JS скрипт прямо в странице
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            stream_data = {"url": None}

            async def handle_request(request):
                u = request.url
                if ".m3u8" in u and not any(x in u for x in ["ads", "log", "stat", "yandex", "doubleclick"]):
                    if any(key in u for key in ["token=", "master", "index", "chunklist"]):
                        stream_data["url"] = u

            page.on("request", handle_request)
            print(f"[*] {name:.<25}", end=" ", flush=True)

            try:
                # Переход с эмуляцией реферера
                await page.goto(url, wait_until="domcontentloaded", timeout=40000)
                await asyncio.sleep(8) 
                
                # Поиск видео и реальный клик (симуляция человека)
                video_box = await page.query_selector("video, .player-container, #player")
                if video_box:
                    box = await video_box.bounding_box()
                    if box:
                        await page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                else:
                    await page.mouse.click(640, 360) 

                # Ожидание ссылки до 15 секунд
                for _ in range(15):
                    if stream_data["url"]: break
                    await asyncio.sleep(1)

                if stream_data["url"]:
                    results.append((name, stream_data["url"]))
                    print("OK", flush=True)
                else:
                    print("FAIL", flush=True)
            except:
                print("ERROR", flush=True)
            finally:
                await context.close()

        if results:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for n, l in results:
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> ГОТОВО! Сохранено {len(results)} каналов.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())












