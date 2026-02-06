import asyncio
import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def get_all_channels_from_site(page):
    print(">>> [1/3] Поиск списка каналов...", flush=True)
    try:
        await page.goto("https://smotrettv.com", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)
        
        found_channels = {}
        # Собираем все ссылки на каналы из разных категорий
        links = await page.query_selector_all("a[href*='/']")
        for link in links:
            try:
                url = await link.get_attribute("href")
                name = await link.inner_text()
                if url and name:
                    clean_name = name.strip().split('\n')[0].upper()
                    # Фильтруем мусорные ссылки и короткие строки
                    if len(clean_name) > 1 and any(cat in url for cat in ['/public/', '/news/', '/sport/', '/entertainment/']):
                        full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                        if clean_name not in found_channels:
                            found_channels[clean_name] = full_url
            except: continue
        
        print(f"    [+] Найдено уникальных каналов: {len(found_channels)}", flush=True)
        return found_channels
    except Exception as e:
        print(f"[!] Ошибка главной страницы: {e}", flush=True)
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> [2/3] Запуск браузера в Stealth-режиме...", flush=True)
        # headless=True можно поменять на False, чтобы видеть процесс
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)

        # Сначала получаем общий список
        base_page = await context.new_page()
        await stealth_async(base_page)
        CHANNELS = await get_all_channels_from_site(base_page)
        await base_page.close()

        if not CHANNELS:
            print("!!! Не удалось получить список каналов. Завершение.")
            await browser.close()
            return

        print(f"\n>>> [3/3] Сбор прямых ссылок (максимум 20)...", flush=True)
        results = []
        
        # Ограничиваем до 20, чтобы не получить бан по IP быстро
        for name, url in list(CHANNELS.items())[:20]:
            # Создаем НОВУЮ вкладку для каждого канала
            page = await context.new_page()
            await stealth_async(page)
            
            # Локальный контейнер для ссылки текущего канала
            stream_data = {"url": None}

            async def handle_request(request):
                u = request.url
                # Ищем m3u8, исключая рекламу и метрику
                if ".m3u8" in u and not any(x in u for x in ["yandex", "ads", "log", "telemetry", "stat"]):
                    if "token=" in u or "master" in u or "index" in u or "playlist" in u:
                        stream_data["url"] = u

            page.on("request", handle_request)
            print(f"[*] {name:.<25}", end=" ", flush=True)

            try:
                # Переходим на страницу канала
                await page.goto(url, wait_until="domcontentloaded", timeout=40000)
                await asyncio.sleep(6) # Время на инициализацию плеера

                # Симуляция клика в центр плеера для запуска потока
                await page.mouse.click(640, 360)
                
                # Ждем появления ссылки до 10 секунд
                for _ in range(10):
                    if stream_data["url"]: break
                    await asyncio.sleep(1)

                if stream_data["url"]:
                    results.append((name, stream_data["url"]))
                    print("OK", flush=True)
                else:
                    print("FAIL (нет m3u8)", flush=True)
            except Exception:
                print("TIMEOUT", flush=True)
            finally:
                # Закрываем вкладку обязательно, чтобы очистить память и запросы
                await page.close()

        # Запись в файл
        if results:
            filename = "playlist.m3u"
            with open(filename, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write(f"# Сгенерировано: {datetime.datetime.now()}\n")
                for n, l in results:
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> ГОТОВО! Сохранено {len(results)} каналов в {filename}")

        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(get_tokens_and_make_playlist())
    except KeyboardInterrupt:
        pass












