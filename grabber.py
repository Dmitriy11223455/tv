import asyncio
import datetime
import os
import random
from playwright.async_api import async_playwright

# Мобильный User-Agent (обходит 90% защит и дает стабильные потоки)
USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"

async def scroll_page(page):
    """Прокрутка для подгрузки плиток каналов"""
    for _ in range(4):
        await page.mouse.wheel(0, 2500)
        await asyncio.sleep(2)

async def get_all_channels_from_site(page):
    print(">>> [1/2] Обход всех разделов ТВ (глубокий поиск)...", flush=True)
    sections = [
        "https://smotrettv.com/top.html",
        "https://smotrettv.com/tv/page/2/",
        "https://smotrettv.com/tv/page/3/",
        "https://smotrettv.com/tv/page/4/",
        "https://smotrettv.com/tv/page/5/"
    ]
    
    found = {}
    for section_url in sections:
        try:
            print(f"    [*] Категория: {section_url.split('/')[-2].upper()}", flush=True)
            await page.goto(section_url, wait_until="commit", timeout=60000)
            await asyncio.sleep(4)
            await scroll_page(page)
            
            # Собираем ссылки на страницы каналов
            links = await page.query_selector_all("a[href*='.html']")
            for link in links:
                try:
                    url = await link.get_attribute("href")
                    name = await link.inner_text()
                    if url and name and len(name.strip()) > 2:
                        clean = name.strip().split('\n')[0].upper()
                        full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                        if clean not in found:
                            found[clean] = full_url
                except: continue
        except: continue
        
    print(f"    [+] Найдено ТВ каналов: {len(found)}", flush=True)
    return found

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> [2/2] Запуск Stealth-браузера...", flush=True)
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        
        # Эмуляция iPhone для обхода защит Mediavitrina и Musical.uz
        device = p.devices['iPhone 12']
        context = await browser.new_context(**device, locale="ru-RU")
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        temp_page = await context.new_page()
        CHANNELS = await get_all_channels_from_site(temp_page)
        await temp_page.close()

        if not CHANNELS:
            await browser.close()
            return

        print(f"\n>>> Сбор прямых ссылок (Лимит: 50 для скорости)...", flush=True)
        results = []
        
        # Сортировка: Россия 1 и Первый в начало
        sorted_keys = sorted(CHANNELS.keys(), key=lambda x: ("РОССИЯ 1" not in x, "ПЕРВЫЙ" not in x, x))
        
        for name in sorted_keys[:150]:
            url = CHANNELS[name]
            ch_page = await context.new_page()
            captured_urls = []

            async def handle_request(request):
                u = request.url
                if ".m3u8" in u and not any(x in u for x in ["ads", "yandex", "metrika", "telemetry"]):
                    captured_urls.append(u)

            ch_page.on("request", handle_request)
            print(f"[*] {name:.<25}", end=" ", flush=True)

            try:
                await ch_page.goto(url, wait_until="commit", timeout=60000)
                await asyncio.sleep(12)
                
                # Клик по плееру
                await ch_page.mouse.click(200, 300) 
                
                for _ in range(25):
                    if captured_urls: break
                    await asyncio.sleep(1)

                if captured_urls:
                    # УМНЫЙ ВЫБОР: Сначала ищем Master-плейлисты (index или master)
                    masters = [u for u in captured_urls if any(x in u for x in ["index.m3u8", "master.m3u8"])]
                    # Если нет мастеров, ищем v4 (720p) для Wi-Fi
                    wifi_v = [u for u in captured_urls if "v4" in u or "720" in u]
                    
                    if masters:
                        final_link = masters[-1] # Последний найденный мастер самый свежий
                    elif wifi_v:
                        final_link = wifi_v[0]
                    else:
                        final_link = max(captured_urls, key=len)
                        
                    results.append((name, str(final_link)))
                    print("OK", flush=True)
                else:
                    # Запасной метод JS (вытаскиваем src прямо из тега video)
                    src = await ch_page.evaluate("() => document.querySelector('video') ? document.querySelector('video').src : null")
                    if src and "http" in src:
                        results.append((name, src))
                        print("OK (JS)", flush=True)
                    else:
                        print("FAIL", flush=True)
            except:
                print("ERR", flush=True)
            finally:
                await ch_page.close()

        # ЗАПИСЬ В ПЛЕЙЛИСТ
        if results:
            filename = "playlist.m3u"
            with open(filename, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write(f"# Сгенерировано: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                for n, l in results:
                    f.write(f'#EXTINF:-1, {n}\n')
                    # Фикс заголовков для Mediavitrina и Musical.uz
                    if any(x in l for x in ["mediavitrina", "musical.uz"]) or any(x in n for x in ["РОССИЯ 1", "ПЕРВЫЙ", "НТВ"]):
                        h = f"|Referer=https://player.mediavitrina.ru{USER_AGENT}"
                    else:
                        h = f"|Referer=https://smotrettv.com{USER_AGENT}"
                    f.write(f"{l}{h}\n\n")
            print(f"\n>>> ГОТОВО! Плейлист {filename} создан ({len(results)} каналов)")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())


















