import asyncio
import datetime
import sys
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def get_all_channels_from_site(page):
    print(">>> [1/3] Загрузка главной страницы сайта...", flush=True)
    try:
        await page.goto("https://smotrettv.com", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)
        
        found_channels = {}
        links = await page.query_selector_all("a")
        print(f">>> Найдено сырых ссылок на странице: {len(links)}", flush=True)
        
        for link in links:
            try:
                url = await link.get_attribute("href")
                raw_name = await link.inner_text()
                
                if url and raw_name:
                    # Корректная очистка имени
                    clean_name = raw_name.split('\n')[0].strip().upper()
                    
                    if len(clean_name) < 2: continue

                    categories = ['/public/', '/entertainment/', '/news/', '/kids/', '/movies/', '/sport/']
                    if any(cat in url for cat in categories):
                        if clean_name not in found_channels:
                            full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                            found_channels[clean_name] = full_url
                            print(f"    [+] Определен канал: {clean_name}", flush=True)
            except:
                continue
            
        return found_channels
    except Exception as e:
        print(f"[!] Ошибка при сборе списка: {e}", flush=True)
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> [2/3] Запуск браузера Chromium...", flush=True)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        
        CHANNELS = await get_all_channels_from_site(page)
        
        if not CHANNELS:
            print("[!] ОШИБКА: Список каналов пуст. Завершение.", flush=True)
            await browser.close()
            return

        print(f"\n>>> [3/3] Начинаю захват токенов для {len(CHANNELS)} каналов...", flush=True)
        
        playlist_results = []
        for name, url in CHANNELS.items():
            stream_url = None

            async def catch_m3u8(request):
                nonlocal stream_url
                r_url = request.url
                if ".m3u8" in r_url and not any(x in r_url for x in ["yandex", "ads", "doubleclick", "telemetree"]):
                    if any(key in r_url for key in ["token=", "mediavitrina", "master", "index"]):
                        stream_url = r_url

            page.on("request", catch_m3u8)
            print(f"[*] Проверка: {name:.<25}", end=" ", flush=True)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(7) 

                # Эмуляция активности для запуска плеера
                for frame in page.frames:
                    try:
                        await frame.click("video", timeout=500, force=True)
                    except:
                        pass
                await page.keyboard.press("Space")
                
                # Ждем перехвата ссылки 10 секунд
                for _ in range(10):
                    if stream_url: break
                    await asyncio.sleep(1)
                
                if stream_url:
                    playlist_results.append((name, stream_url))
                    print("ПОЙМАН", flush=True)
                else:
                    # Финальная попытка клика по центру
                    await page.mouse.click(640, 360)
                    await asyncio.sleep(3)
                    if stream_url:
                        playlist_results.append((name, stream_url))
                        print("ПОЙМАН (v2)", flush=True)
                    else:
                        print("ПРОПУСК", flush=True)
            except:
                print("ТАЙМАУТ", flush=True)
            
            page.remove_listener("request", catch_m3u8)

        if playlist_results:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write(f"# UPDATED: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for n, l in playlist_results:
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> ГОТОВО! Файл playlist.m3u создан. Каналов: {len(playlist_results)}", flush=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())









