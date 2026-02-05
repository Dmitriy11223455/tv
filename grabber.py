import asyncio
import random
import datetime
from playwright.async_api import async_playwright

AGENTS = [
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36"
]

async def get_all_channels_from_site(page):
    now = lambda: datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now()}] >>> Поиск каналов (Ручной Stealth)...")
    try:
        await page.goto("https://smotret.tv", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(10)
        
        for i in range(1, 4):
            await page.evaluate("window.scrollBy(0, 1200)")
            await asyncio.sleep(2)

        found_channels = {}
        links = await page.query_selector_all("a[href*='.html']")
        
        for el in links:
            url = await el.get_attribute("href")
            title = await el.get_attribute("title") or await el.inner_text()
            
            if url and title and any(c.isdigit() for c in url):
                if any(x in url for x in ["about", "contact", "rules", "dmca"]): continue
                full_url = url if url.startswith("http") else f"https://smotret.tv{url}"
                clean_name = title.strip().split('\n')[0]
                if full_url not in found_channels.values() and len(clean_name) > 1:
                    found_channels[clean_name] = full_url
        
        print(f"[{now()}] [OK] Найдено каналов: {len(found_channels)}")
        return found_channels
    except Exception as e:
        print(f"[{now()}] [!] Ошибка сканирования: {e}")
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        now_ts = lambda: datetime.datetime.now().strftime("%H:%M:%S")
        ua = random.choice(AGENTS)
        print(f"\n[{now_ts()}] >>> Запуск браузера с ручной маскировкой...")
        
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=ua,
            viewport={'width': 450, 'height': 900},
            is_mobile=True,
            has_touch=True
        )
        page = await context.new_page()
        
        # --- РУЧНОЙ STEALTH (ЗАМЕНА БИБЛИОТЕКИ) ---
        await page.add_init_script("""
            # Удаляем флаг автоматизации
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            # Подменяем количество языков и плагины
            Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en-US'] });
            window.chrome = { runtime: {} };
        """)
        print(f"[{now_ts()}] >>> Маскировка применена.")
        
        CHANNELS = await get_all_channels_from_site(page)
        if not CHANNELS:
            print(f"[{now_ts()}] [!] Список пуст. IP GitHub в бане.")
            await browser.close()
            return

        await page.route("**/*.{png,jpg,jpeg,gif,webp,svg}", lambda route: route.abort())
        
        playlist_results = []
        target_list = list(CHANNELS.items())

        for counter, (name, url) in enumerate(target_list, 1):
            ts = now_ts()
            print(f"[{ts}] [{counter}/{len(target_list)}] Граббинг: {name}")
            current_stream = None

            async def catch_m3u8(request):
                nonlocal current_stream
                if ".m3u8" in request.url and len(request.url) > 60:
                    if not any(x in request.url for x in ["/ads/", "track", "pixel"]):
                        current_stream = request.url

            page.on("request", catch_m3u8)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(8)
                await page.mouse.click(225, 350)
                await asyncio.sleep(6)
                if current_stream:
                    playlist_results.append((name, current_stream))
                    print(f"   [+] OK")
            except: pass
            page.remove_listener("request", catch_m3u8)

        if playlist_results:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for n, l in playlist_results:
                    f.write(f'#EXTINF:-1, {n}\n{l}|Referer=https://smotrettv.com{ua}\n')
            print(f"\n[{now_ts()}] ИТОГ: Собрано {len(playlist_results)} каналов.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())




