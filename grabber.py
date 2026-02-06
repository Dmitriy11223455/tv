import asyncio
import datetime
from playwright.async_api import async_playwright
# Правильный импорт функции
from playwright_stealth import stealth

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def get_all_channels_from_site(page):
    print(">>> [1/3] Поиск списка каналов...", flush=True)
    try:
        await page.goto("https://smotrettv.com", wait_until="domcontentloaded", timeout=60000)
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
        print(f"[!] Ошибка: {e}", flush=True)
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> [2/3] Запуск браузера...", flush=True)
        browser = await p.chromium.launch(headless=True)
        
        # Основной контекст для сбора списка
        context = await browser.new_context(user_agent=USER_AGENT)
        temp_page = await context.new_page()
        # ИСПОЛЬЗУЕМ ФУНКЦИЮ ПРАВИЛЬНО
        await stealth(temp_page) 
        
        CHANNELS = await get_all_channels_from_site(temp_page)
        await temp_page.close()
        await context.close()

        if not CHANNELS: 
            print("Каналы не найдены")
            return await browser.close()

        print(f"\n>>> [3/3] Сбор ссылок (изолированно)...", flush=True)
        results = []
        
        for name, url in list(CHANNELS.items())[:20]:
            # НОВАЯ СЕССИЯ ДЛЯ КАЖДОГО КАНАЛА (решает проблему дублей видео)
            ch_context = await browser.new_context(user_agent=USER_AGENT)
            page = await ch_context.new_page()
            await stealth(page)
            
            stream_data = {"url": None}

            async def handle_request(request):
                u = request.url
                if ".m3u8" in u and not any(x in u for x in ["ads", "log", "stat", "yandex"]):
                    if "token=" in u or "master" in u or "index" in u:
                        stream_data["url"] = u

            page.on("request", handle_request)
            print(f"[*] {name:.<25}", end=" ", flush=True)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=40000)
                await asyncio.sleep(10)
                # Клик для запуска, если поток не пошел сам
                await page.mouse.click(640, 360) 
                
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
                await ch_context.close()

        if results:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for n, l in results:
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> ГОТОВО! Ссылок: {len(results)}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())













