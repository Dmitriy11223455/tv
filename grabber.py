import asyncio
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def get_all_channels_from_site(page):
    print(">>> Сбор уникального списка каналов...")
    try:
        # Ждем загрузки сети, чтобы JS успел отрисовать элементы
        await page.goto("https://smotrettv.com", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)
        
        found_channels = {}
        links = await page.query_selector_all("a")
        
        for link in links:
            try:
                url = await link.get_attribute("href")
                name = await link.inner_text()
                
                if url and name and len(name.strip()) > 1:
                    categories = ['/public/', '/entertainment/', '/news/', '/kids/', '/movies/', '/sport/']
                    if any(cat in url for cat in categories):
                        # ИСПРАВЛЕНО: Сначала очищаем текст, потом приводим к регистру
                        clean_name = name.strip().split('\n')[0].strip().upper()
                        
                        if len(clean_name) > 2 and clean_name not in found_channels:
                            full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                            found_channels[clean_name] = full_url
            except:
                continue
            
        return found_channels
    except Exception as e:
        print(f"[!] Ошибка при сборе каналов: {e}")
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> Запуск браузера...")
        # ИСПРАВЛЕНО: headless=True обязателен для GitHub Actions
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        
        # Блокируем картинки для экономии трафика и скорости
        await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2}", lambda route: route.abort())

        CHANNELS = await get_all_channels_from_site(page)
        
        if not CHANNELS:
            print("[!] Список каналов пуст. Возможно, сайт заблокировал доступ или изменил структуру.")
            await browser.close()
            return

        print(f"[OK] Найдено уникальных каналов: {len(CHANNELS)}")
        
        playlist_results = []
        for name, url in CHANNELS.items():
            print(f"[*] Граббинг: {name}")
            stream_url = None

            async def catch_m3u8(request):
                nonlocal stream_url
                r_url = request.url
                if ".m3u8" in r_url and "yandex" not in r_url and "google" not in r_url:
                    if any(x in r_url for x in ["token=", "mediavitrina", ".m3u8"]):
                        stream_url = r_url

            page.on("request", catch_m3u8)
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(6) # Даем время плееру
                
                # Имитируем клик для запуска плеера
                await page.mouse.click(300, 300)
                
                for _ in range(10):
                    if stream_url: break
                    await asyncio.sleep(1)
                
                if stream_url:
                    playlist_results.append((name, stream_url))
                    print(f"   + Поток пойман")
                else:
                    print(f"   - Не найден")
            except:
                print(f"   ! Ошибка загрузки")
            
            page.remove_listener("request", catch_m3u8)

        if playlist_results:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for n, l in playlist_results:
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> ГОТОВО! Сохранено {len(playlist_results)} каналов.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())








