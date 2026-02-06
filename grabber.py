import asyncio
import datetime
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def get_all_channels_from_site(page):
    print(">>> [1/3] Поиск списка каналов...", flush=True)
    try:
        # Используем "commit" или "domcontentloaded", чтобы проскочить проверку быстрее
        await page.goto("https://smotrettv.com", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(7)
        
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
        
        if not found_channels:
            # Попытка №2 если ссылки не нашлись
            print("    [!] Ссылки не найдены, пробую альтернативный поиск...")
            # Тут можно добавить поиск по кнопкам или другим тегам
            
        print(f"    [+] Найдено каналов: {len(found_channels)}", flush=True)
        return found_channels
    except Exception as e:
        print(f"[!] Ошибка доступа (Timeout): {e}", flush=True)
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> [2/3] Инициализация Chromium...", flush=True)
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"}
        )
        
        page = await context.new_page()
        # Маскировка под реальный браузер
        await page.add_init_script("delete navigator.__proto__.webdriver")
        
        CHANNELS = await get_all_channels_from_site(page)
        
        if not CHANNELS:
            print(">>> [!] Список пуст. Возможно, IP GitHub заблокирован.")
            await browser.close()
            return

        print(f"\n>>> [3/3] Сбор потоков...", flush=True)
        results = []
        
        for name, url in list(CHANNELS.items())[:15]:
            # Важно: каждый канал в своем контексте для изоляции ссылок
            ch_ctx = await browser.new_context(user_agent=USER_AGENT)
            ch_page = await ch_ctx.new_page()
            
            stream_data = {"url": None}

            async def handle_request(request):
                u = request.url
                if ".m3u8" in u and not any(x in u for x in ["ads", "log", "stat", "yandex"]):
                    stream_data["url"] = u

            ch_page.on("request", handle_request)
            print(f"[*] {name:.<25}", end=" ", flush=True)

            try:
                await ch_page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(10)
                
                # Имитация клика в область плеера
                await ch_page.mouse.click(960, 540)
                
                for _ in range(15):
                    if stream_data["url"]: break
                    await asyncio.sleep(1)

                if stream_data["url"]:
                    results.append((name, stream_data["url"]))
                    print("OK", flush=True)
                else:
                    print("FAIL", flush=True)
            except:
                print("ERR", flush=True)
            finally:
                await ch_ctx.close()

        if results:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for n, l in results:
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> ГОТОВО! Сохранено: {len(results)}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())













