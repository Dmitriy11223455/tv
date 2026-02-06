import asyncio
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def get_all_channels_from_site(page):
    print(">>> Загрузка главной страницы...")
    try:
        # Используем wait_until="domcontentloaded" для скорости
        await page.goto("https://smotrettv.com", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)
        
        found_channels = {}
        links = await page.query_selector_all("a")
        print(f">>> Всего ссылок на странице: {len(links)}")
        
        for link in links:
            try:
                url = await link.get_attribute("href")
                raw_name = await link.inner_text()
                
                if url and raw_name:
                    # ИСПРАВЛЕННАЯ ОЧИСТКА ИМЕНИ
                    name_lines = raw_name.split('\n')
                    clean_name = name_lines[0].strip().upper()
                    
                    if not clean_name: continue

                    categories = ['/public/', '/entertainment/', '/news/', '/kids/', '/movies/', '/sport/']
                    if any(cat in url for cat in categories):
                        if clean_name not in found_channels:
                            full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                            found_channels[clean_name] = full_url
                            # Печатаем каждый найденный канал для отладки
                            print(f"    Нашел канал: {clean_name}")
            except Exception as e:
                continue
            
        return found_channels
    except Exception as e:
        print(f"[!] Ошибка при загрузке сайта: {e}")
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> Запуск Chrome...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        
        CHANNELS = await get_all_channels_from_site(page)
        
        if not CHANNELS:
            print("[!] Каналы не найдены. Проверь селекторы или доступ к сайту.")
            await browser.close()
            return

        print(f"\n>>> Итого найдено: {len(CHANNELS)}. Начинаю сбор токенов...")
        
        playlist_results = []
        # Тестируем первые 15 каналов
        for name, url in list(CHANNELS.items())[:15]:
            stream_url = None

            async def catch_m3u8(request):
                nonlocal stream_url
                if ".m3u8" in request.url and not any(x in request.url for x in ["yandex", "ads"]):
                    stream_url = request.url

            page.on("request", catch_m3u8)
            print(f"[*] Обработка: {name}...", end=" ", flush=True)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(5)
                # Клик в центр экрана
                await page.mouse.click(400, 300)
                
                for _ in range(7):
                    if stream_url: break
                    await asyncio.sleep(1)
                
                if stream_url:
                    playlist_results.append((name, stream_url))
                    print("OK")
                else:
                    print("FAIL (нет ссылки)")
            except:
                print("ERROR (таймаут)")
            
            page.remove_listener("request", catch_m3u8)

        if playlist_results:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                import datetime
                f.write(f"# Updated: {datetime.datetime.now()}\n")
                for n, l in playlist_results:
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> Плейлист готов! Сохранено каналов: {len(playlist_results)}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())








