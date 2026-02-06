import asyncio
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

async def get_all_channels_from_site(page):
    print(">>> Сбор уникального списка каналов...")
    try:
        await page.goto("https://smotrettv.com", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        
        # Скроллим для подгрузки динамического контента
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

        found_channels = {}
        # Селектор ссылок на каналы
        links = await page.query_selector_all("a[href*='/public/'], a[href*='/entertainment/'], a[href*='/news/'], a[href*='/kids/'], a[href*='/movies/'], a[href*='/sport/']")
        
        for link in links:
            name = await link.inner_text()
            url = await link.get_attribute("href")
            
            if url and len(name.strip()) > 1:
                # Очистка имени от мусора и перевод в верхний регистр для фильтрации дублей
                clean_name = name.strip().split('\n')[0].strip().upper()
                full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                
                # Если канал с таким именем уже есть — пропускаем (убирает дубли Россия 1, Первый и т.д.)
                if clean_name not in found_channels:
                    found_channels[clean_name] = full_url
            
        return found_channels
    except Exception as e:
        print(f"[!] Ошибка при сборе: {e}")
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> Запуск браузера...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        
        # Блокируем тяжелый контент (картинки, шрифты)
        await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,css}", lambda route: route.abort())

        CHANNELS = await get_all_channels_from_site(page)
        
        if not CHANNELS:
            print("[!] Каналы не найдены.")
            await browser.close()
            return

        print(f"[OK] Найдено уникальных каналов: {len(CHANNELS)}")
        
        playlist_results = []
        
        for name, url in CHANNELS.items():
            print(f"[*] Граббинг: {name}")
            stream_url = None

            # Обработчик перехвата запросов
            async def catch_m3u8(request):
                nonlocal stream_url
                r_url = request.url
                # Игнорируем рекламу и ищем только m3u8 с токенами или привязкой к медиавитрине
                if ".m3u8" in r_url and "yandex" not in r_url and "doubleclick" not in r_url:
                    if any(x in r_url for x in ["token=", "mediavitrina", "index", "master"]):
                        stream_url = r_url

            page.on("request", catch_m3u8)
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(5)
                
                # Попытка нажать на кнопку Play или центр плеера, если поток не пошел сам
                try:
                    await page.click("div[id*='player'], video, .play-button", timeout=3000)
                except:
                    pass
                
                # Ожидание появления ссылки
                for _ in range(8):
                    if stream_url: break
                    await asyncio.sleep(1)
                
                if stream_url:
                    playlist_results.append((name, stream_url))
                    print(f"   + Нашел: {stream_url[:60]}...")
                else:
                    print(f"   - Поток не найден")
            except Exception:
                print(f"   ! Тайм-аут или ошибка")
            
            page.remove_listener("request", catch_m3u8)

        # Сохранение в файл
        if playlist_results:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for n, l in playlist_results:
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> ГОТОВО! Сохранено {len(playlist_results)} каналов в 'playlist.m3u'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())







