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
        for link in links:
            try:
                url = await link.get_attribute("href")
                name = await link.inner_text()
                if url and name:
                    clean_name = name.split('\n')[0].strip().upper()
                    if len(clean_name) < 2: continue
                    # Исключаем лишние разделы, оставляем только потенциальные каналы
                    if any(cat in url for cat in ['/public/', '/news/', '/sport/', '/entertainment/', '/ukraine/']):
                        full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                        if clean_name not in found_channels:
                            found_channels[clean_name] = full_url
            except: continue
        print(f"    [+] Найдено каналов: {len(found_channels)}", flush=True)
        return found_channels
    except Exception as e:
        print(f"[!] Ошибка главной: {e}", flush=True)
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> [2/3] Запуск браузера...", flush=True)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT, viewport={'width': 1280, 'height': 720})
        
        # Сначала получаем список каналов
        temp_page = await context.new_page()
        CHANNELS = await get_all_channels_from_site(temp_page)
        await temp_page.close()

        if not CHANNELS: 
            await browser.close()
            return

        print(f"\n>>> [3/3] Граббинг ссылок (первые 20)...", flush=True)
        results = []
        
        for name, url in list(CHANNELS.items())[:20]:
            # !!! ВАЖНО: новая страница для каждого канала, чтобы избежать дублей из кэша/сессии
            page = await context.new_page()
            current_stream_url = None 

            async def handle_request(request):
                nonlocal current_stream_url
                u = request.url
                # Фильтруем только нужные m3u8, игнорируя рекламу и метрику
                if ".m3u8" in u and not any(x in u for x in ["yandex", "ads", "log", "doubleclick"]):
                    if "token=" in u or "master" in u or "index" in u or "playlist" in u:
                        current_stream_url = u

            page.on("request", handle_request)
            print(f"[*] {name:.<25}", end=" ", flush=True)

            try:
                await page.goto(url, wait_until="load", timeout=30000)
                await asyncio.sleep(4) # Даем время на подгрузку плеера
                
                # Кликаем по плееру для запуска потока
                await page.mouse.click(640, 360) 
                
                # Ждем ссылку 10 секунд
                for _ in range(10):
                    if current_stream_url: break
                    await asyncio.sleep(1)

                if current_stream_url:
                    results.append((name, current_stream_url))
                    print("OK", flush=True)
                else:
                    print("FAIL", flush=True)
            except Exception:
                print("ERROR", flush=True)
            finally:
                await page.close() # Закрываем вкладку канала

        if results:
            filename = "playlist.m3u"
            with open(filename, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for n, l in results:
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> ГОТОВО! Файл {filename} создан. Каналов: {len(results)}", flush=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())












