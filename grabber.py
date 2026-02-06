import asyncio
import random
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def get_all_channels_from_site(page):
    print(">>> Сбор уникального списка каналов...")
    try:
        # Переходим на сайт и ждем загрузки сети
        await page.goto("https://smotrettv.com", wait_until="networkidle", timeout=60000)
        
        # Небольшая пауза для прогрузки JS-сетки
        await asyncio.sleep(5)
        
        found_channels = {}
        # Собираем вообще все ссылки на странице
        links = await page.query_selector_all("a")
        
        for link in links:
            try:
                name = await link.inner_text()
                url = await link.get_attribute("href")
                
                if url and name and len(name.strip()) > 1:
                    # Фильтруем ссылки, которые ведут на разделы с каналами
                    categories = ['/public/', '/entertainment/', '/news/', '/kids/', '/movies/', '/sport/']
                    if any(cat in url for cat in categories):
                        # Чистим имя: убираем переносы, лишние пробелы и в верхний регистр для удаления дублей
                        clean_name = name.strip().split('\n')[0].strip().upper()
                        
                        # Если это не "СМОТРЕТЬ" или "ЭФИР", а реальное название
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
        # Если снова будет 0 каналов, поменяйте headless=True на headless=False
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        
        # Блокируем только тяжелые картинки, чтобы ускорить процесс
        await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2}", lambda route: route.abort())

        CHANNELS = await get_all_channels_from_site(page)
        
        if not CHANNELS:
            print("[!] Ссылки не найдены. Попробуйте запустить с headless=False.")
            await browser.close()
            return

        print(f"[OK] Найдено уникальных каналов: {len(CHANNELS)}")
        
        playlist_results = []
        
        # Проходим по списку каналов
        for name, url in CHANNELS.items():
            print(f"[*] Граббинг: {name}")
            stream_url = None

            async def catch_m3u8(request):
                nonlocal stream_url
                r_url = request.url
                # Ищем m3u8, отсекая рекламу
                if ".m3u8" in r_url and "yandex" not in r_url and "google" not in r_url:
                    # Нам нужен поток с токеном или с домена трансляции
                    if any(x in r_url for x in ["token=", "mediavitrina", ".m3u8"]):
                        stream_url = r_url

            page.on("request", catch_m3u8)
            
            try:
                # Заходим на страницу канала
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(4) # Ждем инициализации плеера
                
                # Кликаем в область плеера, чтобы запустить поток
                await page.mouse.click(640, 400)
                
                # Ждем появления ссылки в сетевых запросах
                for _ in range(10):
                    if stream_url: break
                    await asyncio.sleep(1)
                
                if stream_url:
                    playlist_results.append((name, stream_url))
                    print(f"   + Поток пойман")
                else:
                    print(f"   - Ссылка не найдена")
            except Exception:
                print(f"   ! Ошибка загрузки страницы")
            
            # Убираем слушателя перед следующим каналом
            page.remove_listener("request", catch_m3u8)

        # Сохранение итогового плейлиста
        if playlist_results:
            filename = "playlist.m3u"
            with open(filename, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for n, l in playlist_results:
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> УСПЕХ! Создан файл: {filename}")
            print(f">>> Всего каналов: {len(playlist_results)}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())








