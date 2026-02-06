import asyncio
import datetime
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def get_all_channels_from_site(page):
    print(">>> [1/3] Загрузка списка каналов...", flush=True)
    try:
        await page.goto("https://smotrettv.com", wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(5)
        found_channels = {}
        links = await page.query_selector_all("a")
        
        stop_names = ["ОБЩЕСТВЕННЫЕ", "НОВОСТНЫЕ", "СПОРТИВНЫЕ", "РАЗВЛЕКАТЕЛЬНЫЕ", "ДЕТСКИЕ", "ФИЛЬМЫ", "ПОЗНАВАТЕЛЬНЫЕ", "ЭФИР", "СМОТРЕТЬ"]

        for link in links:
            try:
                url = await link.get_attribute("href")
                name = await link.inner_text()
                if url and name:
                    clean_name = name.split('\n')[0].strip().upper()
                    if len(clean_name) < 3 or clean_name in stop_names: continue
                    
                    if any(cat in url for cat in ['/public/', '/news/', '/sport/', '/entertainment/']):
                        full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                        if clean_name not in found_channels:
                            found_channels[clean_name] = full_url
                            print(f"    [+] {clean_name}", flush=True)
            except: continue
        return found_channels
    except Exception as e:
        print(f"[!] Ошибка: {e}", flush=True)
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> [2/3] Запуск браузера...", flush=True)
        browser = await p.chromium.launch(headless=True)
        # Добавляем Referer, чтобы сайт думал, что мы перешли с главной
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1280, 'height': 720},
            extra_http_headers={"Referer": "https://smotrettv.com"}
        )
        page = await context.new_page()

        CHANNELS = await get_all_channels_from_site(page)
        if not CHANNELS: return

        print(f"\n>>> [3/3] Граббинг токенов...", flush=True)
        results = {}
        
        for name, url in CHANNELS.items():
            stream_url = None
            
            async def handle_request(request):
                nonlocal stream_url
                u = request.url
                # Ослабляем фильтр: ловим всё, что похоже на поток
                if ".m3u8" in u and not any(x in u for x in ["yandex", "doubleclick", "telemetree"]):
                    stream_url = u

            page.on("request", handle_request)
            print(f"[*] {name:.<22}", end=" ", flush=True)

            try:
                # Переходим и имитируем задержку как у человека
                await page.goto(url, wait_until="load", timeout=30000)
                await asyncio.sleep(8)
                
                # Кликаем по плееру в разных точках
                await page.mouse.click(640, 360)
                await asyncio.sleep(1)
                await page.keyboard.press("Space")
                
                # Ждем поток 12 секунд
                for _ in range(12):
                    if stream_url: break
                    await asyncio.sleep(1)

                if stream_url:
                    results[name] = stream_url
                    print("OK", flush=True)
                else:
                    # Пробуем найти iframe и кликнуть в нем
                    for frame in page.frames:
                        try:
                            await frame.click("body", timeout=1000)
                        except: pass
                    await asyncio.sleep(3)
                    if stream_url:
                        results[name] = stream_url
                        print("OK (IFRAME)", flush=True)
                    else:
                        print("FAIL", flush=True)
            except:
                print("TIME", flush=True)
            
            page.remove_listener("request", handle_request)

        if results:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write(f"# UPDATED: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n")
                for n, l in results.items():
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> ГОТОВО! Сохранено: {len(results)}", flush=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())











