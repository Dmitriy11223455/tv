import asyncio
import datetime
import sys
from playwright.async_api import async_playwright

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

async def get_all_channels_from_site(page):
    print(">>> [1/3] Загрузка главной страницы...", flush=True)
    try:
        # Уходим от networkidle к commit, чтобы не ждать вечно ответа от заблокированных ресурсов
        await page.goto("https://smotrettv.com/", wait_until="domcontentloaded", timeout=40000)
        
        # Ждем именно появления сетки каналов вручную
        try:
            await page.wait_for_selector("a[href*='/']", timeout=15000)
        except:
            print("[!] Сетка каналов не отрисовалась вовремя.", flush=True)

        found_channels = {}
        links = await page.query_selector_all("a")
        
        for link in links:
            try:
                url = await link.get_attribute("href")
                raw_name = await link.inner_text()
                
                if url and raw_name:
                    clean_name = raw_name.split('\n')[0].strip().upper()
                    if len(clean_name) < 2: continue

                    categories = ['/public/', '/entertainment/', '/news/', '/kids/', '/movies/', '/sport/']
                    if any(cat in url for cat in categories):
                        if clean_name not in found_channels:
                            full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                            found_channels[clean_name] = full_url
                            print(f"    [+] Канал: {clean_name}", flush=True)
            except:
                continue
            
        return found_channels
    except Exception as e:
        print(f"[!] Ошибка доступа: {e}", flush=True)
        return {}

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        print(">>> [2/3] Запуск браузера...", flush=True)
        # Добавляем аргументы для обхода детектирования
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        
        CHANNELS = await get_all_channels_from_site(page)
        
        if not CHANNELS:
            # Если всё еще пусто, делаем скриншот для отладки (сохранится в артефактах GitHub)
            await page.screenshot(path="debug_screen.png")
            print("[!] Список пуст. Скриншот сохранен в debug_screen.png", flush=True)
            await browser.close()
            return

        print(f"\n>>> [3/3] Захват токенов для {len(CHANNELS)} каналов...", flush=True)
        
        playlist_results = []
        # Сократим до 15 каналов для надежности прохождения GitHub Action
        for name, url in list(CHANNELS.items())[:15]:
            stream_url = None

            async def catch_m3u8(request):
                nonlocal stream_url
                if ".m3u8" in request.url and "token" in request.url:
                    stream_url = request.url

            page.on("request", catch_m3u8)
            print(f"[*] {name:.<20}", end=" ", flush=True)

            try:
                # Переходим быстро
                await page.goto(url, wait_until="commit", timeout=20000)
                await asyncio.sleep(8) 
                
                # Клик по плееру
                await page.mouse.click(500, 300)
                
                for _ in range(8):
                    if stream_url: break
                    await asyncio.sleep(1)
                
                if stream_url:
                    playlist_results.append((name, stream_url))
                    print("OK", flush=True)
                else:
                    print("FAIL", flush=True)
            except:
                print("TIME", flush=True)
            
            page.remove_listener("request", catch_m3u8)

        if playlist_results:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write(f"# UPDATED: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                for n, l in playlist_results:
                    f.write(f"#EXTINF:-1, {n}\n{l}\n")
            print(f"\n>>> Плейлист готов!", flush=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())









