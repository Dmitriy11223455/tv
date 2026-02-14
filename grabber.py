import asyncio
import datetime
import os
import random
from playwright.async_api import async_playwright

# Актуальный User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

async def scroll_page(page):
    """Прокрутка для подгрузки всех каналов на главной"""
    print(">>> Прокрутка страницы для поиска новых каналов...", flush=True)
    for _ in range(5):
        await page.mouse.wheel(0, 2000)
        await asyncio.sleep(2)

async def get_all_channels_from_site(page):
    print(">>> [1/3] Автоматический поиск новых каналов...", flush=True)
    try:
        await page.goto("https://smotrettv.com", wait_until="commit", timeout=60000)
        await asyncio.sleep(5)
        await scroll_page(page)
        
        found_channels = {}
        links = await page.query_selector_all("a")
        for link in links:
            try:
                url = await link.get_attribute("href")
                name = await link.inner_text()
                if url and name:
                    clean_name = name.strip().split('\n')[0].upper()
                    if len(clean_name) > 1 and any(x in url for x in ['/public/', '/news/', '/sport/', '/entertainment/']):
                        full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                        if clean_name not in found_channels:
                            found_channels[clean_name] = full_url
            except: continue
        return found_channels
    except Exception as e:
        print(f"[!] Ошибка парсинга: {e}", flush=True)
        return {}

async def get_tokens_and_make_playlist():
    # --- ТВОЙ ОБНОВЛЕННЫЙ СЛОВАРЬ (Новые рабочие ссылки) ---
    MY_CHANNELS = {
        "РОССИЯ 1": "https://smotrettv.com/784-rossija-1.html",
        "НТВ": "https://smotrettv.com/6-ntv.html",
        "РЕН ТВ": "https://smotrettv.com/316-ren-tv.html",
        "ПЕРВЫЙ КАНАЛ": "https://smotrettv.com"
    }

    async with async_playwright() as p:
        print(">>> [2/3] Запуск браузера (Stealth Mode)...", flush=True)
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent=USER_AGENT, viewport={'width': 1280, 'height': 720}, locale="ru-RU")
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        temp_page = await context.new_page()
        SCRAPED = await get_all_channels_from_site(temp_page)
        await temp_page.close()

        # Объединяем словарь и найденное
        for name, url in SCRAPED.items():
            if name not in MY_CHANNELS:
                MY_CHANNELS[name] = url

        print(f"\n>>> [3/3] Сбор ссылок (Всего в очереди: {len(MY_CHANNELS)})...", flush=True)
        results = []
        
        # Лимит 60 каналов для стабильности GitHub Actions
        for name, url in list(MY_CHANNELS.items())[:60]:
            ch_page = await context.new_page()
            captured_urls = []

            async def handle_request(request):
                u = request.url
                if ".m3u8" in u and not any(x in u for x in ["ads", "log", "stat", "yandex", "metrika", "telemetry"]):
                    captured_urls.append(u)

            ch_page.on("request", handle_request)
            print(f"[*] {name:.<25}", end=" ", flush=True)

            try:
                await ch_page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(8)
                
                # Скролл к плееру и клик
                await ch_page.evaluate("window.scrollTo(0, 450)")
                await asyncio.sleep(2)

                selectors = ["video", ".vjs-big-play-button", "button[class*='play']", "#player", "canvas"]
                success_click = False
                for s in selectors:
                    try:
                        el = await ch_page.wait_for_selector(s, timeout=3000)
                        if el:
                            await el.click(force=True)
                            success_click = True
                            break
                    except: continue
                
                if not success_click:
                    await ch_page.mouse.click(640, 480)

                # Ожидание ссылки (25 сек)
                for _ in range(25):
                    if captured_urls: break
                    await asyncio.sleep(1)

                if captured_urls:
                    # ИСПРАВЛЕНИЕ: Выбираем строку, а не список []
                    wifi_v = [u for u in captured_urls if "v4" in u or "720" in u or "mid" in u]
                    final_link = wifi_v[0] if wifi_v else max(captured_urls, key=len)
                    
                    results.append((name, final_link))
                    print("OK", flush=True)
                else:
                    print("FAIL", flush=True)

            except Exception:
                print("ERR", flush=True)
            finally:
                await ch_page.close()

        # ЗАПИСЬ ПЛЕЙЛИСТА
        if results:
            filename = "playlist.m3u"
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("#EXTM3U\n")
                    f.write(f"# Обновлено: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                    
                    for n, l in results:
                        f.write(f'#EXTINF:-1, {n}\n')
                        # ИСПРАВЛЕНИЕ: Формат заголовков (Referer + &User-Agent)
                        if "mediavitrina" in l or any(x in n for x in ["РОССИЯ 1", "НТВ", "РЕН ТВ"]):
                            h = f"|Referer=https://player.mediavitrina.ru{USER_AGENT}"
                        else:
                            h = f"|Referer=https://smotrettv.com{USER_AGENT}"
                        
                        f.write(f"{l}{h}\n\n")
                print(f"\n>>> ГОТОВО! Плейлист {filename} создан. Каналов: {len(results)}")
            except Exception as e:
                print(f"\n[!] Ошибка записи: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())
















