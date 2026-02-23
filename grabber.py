import asyncio
import datetime
import os
import random
from playwright.async_api import async_playwright

# Актуальный User-Agent на 2026 год
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

async def scroll_page(page):
    """Прокрутка для подгрузки списка каналов и радио"""
    for _ in range(3):
        await page.mouse.wheel(0, 2000)
        await asyncio.sleep(2)

async def get_all_channels_from_site(page):
    print(">>> [1/3] Поиск списка всех каналов и радио...", flush=True)
    try:
        await page.goto("https://smotrettv.com", wait_until="commit", timeout=60000)
        await asyncio.sleep(5)
        await scroll_page(page)
        found = {}
        links = await page.query_selector_all("a")
        for link in links:
            try:
                url = await link.get_attribute("href")
                name = await link.inner_text()
                if url and name:
                    clean = name.strip().split('\n')[0].upper()
                    # Ищем ТВ и Радио (.html, /public/ или /radio/)
                    if len(clean) > 1 and any(x in url for x in [".html", "/public/", "/radio/"]):
                        full_url = url if url.startswith("http") else f"https://smotrettv.com{url}"
                        if clean not in found: found[clean] = full_url
            except: continue
        return found
    except Exception as e:
        print(f"[!] Ошибка парсинга: {e}", flush=True)
        return {}

async def main():
    MY_CHANNELS = {
        "РОССИЯ 1": "https://smotrettv.com/784-rossija-1.html",
        "НТВ": "https://smotrettv.com/6-ntv.html",
        "РЕН ТВ": "https://smotrettv.com/316-ren-tv.html",
        "ПЕРВЫЙ КАНАЛ": "https://smotrettv.com/tv/public/1003-pervyj-kanal.html",
        "РОССИЯ 24": "https://smotrettv.com/tv/news/217-rossija-24.html",
        "РТР ПЛАНЕТА": "https://smotrettv.com/tv/public/218-rtr-planeta.html",
        "КАНАЛ Ю": "https://smotrettv.com/tv/entertainment/44-kanal-ju.html"
    }

    async with async_playwright() as p:
        print(">>> [2/3] Запуск браузера (Headless Mode)...", flush=True)
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )

        context = await browser.new_context(user_agent=USER_AGENT, viewport={'width': 1280, 'height': 720})
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        temp_page = await context.new_page()
        SCRAPED = await get_all_channels_from_site(temp_page)
        await temp_page.close()

        # Объединяем твой словарь и найденное
        for name, url in SCRAPED.items():
            if name not in MY_CHANNELS: MY_CHANNELS[name] = url

        print(f"\n>>> [3/3] Сбор прямых ссылок (Лимит: 75)...", flush=True)
        results = []
        
        for name, url in list(MY_CHANNELS.items())[:75]:
            ch_page = await context.new_page()
            captured_urls = []

            async def handle_request(request):
                u = request.url
                # Ловим ТВ (.m3u8) и Радио (.mp3, .aac, stream)
                if any(ext in u.lower() for ext in [".m3u8", ".mp3", ".aac", "stream"]) and not any(x in u for x in ["ads", "yandex", "metrika"]):
                    captured_urls.append(u)

            ch_page.on("request", handle_request)
            print(f"[*] {name:.<25}", end=" ", flush=True)

            try:
                await ch_page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(12) 
                
                # Клик для активации плеера
                await ch_page.evaluate("window.scrollTo(0, 450)")
                play_selectors = ["video", "audio", ".vjs-big-play-button", "button[class*='play']", "div[id*='player']"]
                for s in play_selectors:
                    try:
                        el = await ch_page.wait_for_selector(s, timeout=3000)
                        if el: 
                            await el.click(force=True)
                            await asyncio.sleep(1)
                            break
                    except: continue

                await ch_page.mouse.click(640, 450)
                
                # Ждем появления ссылок
                for _ in range(25):
                    if captured_urls: break
                    await asyncio.sleep(1)

                # СПЕЦИАЛЬНАЯ ЛОГИКА ДЛЯ РОССИИ 1 (OK JS)
                if "РОССИЯ 1" in name:
                    js_src = await ch_page.evaluate("() => { let v = document.querySelector('video'); return v ? v.src : null; }")
                    if js_src and "http" in js_src:
                        results.append((name, js_src))
                        print("OK (JS)", flush=True)
                    else:
                        print("FAIL (JS)", flush=True)
                
                # ОБЫЧНАЯ ЛОГИКА ДЛЯ ВСЕХ ОСТАЛЬНЫХ
                elif captured_urls:
                    # Приоритет радио на mp3, ТВ на master/index
                    audio_v = [u for u in captured_urls if any(x in u.lower() for x in [".mp3", ".aac"])]
                    masters = [u for u in captured_urls if any(x in u.lower() for x in ["master", "index"])]
                    
                    if audio_v:
                        final_link = audio_v[0]
                    elif masters:
                        final_link = masters[-1]
                    else:
                        final_link = max(captured_urls, key=len)
                        
                    results.append((name, str(final_link)))
                    print("OK", flush=True)
                else:
                    # Запасной JS для всех, если m3u8 не поймался
                    src = await ch_page.evaluate("() => { let a = document.querySelector('audio'); let v = document.querySelector('video'); return a ? a.src : (v ? v.src : null); }")
                    if src and "http" in src:
                        results.append((name, src))
                        print("OK (JS)", flush=True)
                    else:
                        print("FAIL", flush=True)
            except:
                print("ERR", flush=True)
            finally:
                await ch_page.close()

        if results:
            filename = "playlist.m3u"
            with open(filename, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n\n")
                for n, l in results:
                    f.write(f'#EXTINF:-1, {n}\n')
                    # Фикс заголовков: слэш после домена и & перед User-Agent
                    if "mediavitrina" in l or any(x in n for x in ["РОССИЯ 1", "НТВ", "РЕН ТВ", "ПЕРВЫЙ", "РОССИЯ 24"]):
                        h = f"|Referer=https://player.mediavitrina.ru{USER_AGENT}"
                    else:
                        h = f"|Referer=https://smotrettv.com{USER_AGENT}"
                    f.write(f"{l}{h}\n\n")
            print(f"\n>>> ГОТОВО! Создан {filename}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())





































