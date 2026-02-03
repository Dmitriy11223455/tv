import asyncio
import os
from playwright.async_api import async_playwright

CHANNELS = {
    "Первый канал": "https://smotrettv.com/1003-pervyj-kanal.html",
    "Россия 1": "https://smotrettv.com/784-rossija-1.html",
    "Звезда": "https://smotrettv.com/310-zvezda.html",
    "ТНТ": "https://smotrettv.com/329-tnt.html",
    "Россия 24": "https://smotrettv.com/217-rossija-24.html",
    "СТС": "https://smotrettv.com/783-sts.html",
    "НТВ": "https://smotrettv.com/6-ntv.html",
    "Рен ТВ": "https://smotrettv.com/316-ren-tv.html"
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

async def grab_channel(browser, name, url):
    stream_url = None
    context = await browser.new_context(user_agent=USER_AGENT)
    page = await context.new_page()
    
    # Создаем папку для скриншотов ошибок
    if not os.path.exists("errors"):
        os.makedirs("errors")

    async def handle_request(request):
        nonlocal stream_url
        if ".m3u8" in request.url and not any(x in request.url for x in ["ads", "yandex", "metrika"]):
            if not stream_url:
                stream_url = request.url
                print(f"   [!] {name}: Ссылка поймана!")

    page.on("request", handle_request)
    
    try:
        print(f"[*] {name}: Загрузка страницы...")
        # Используем networkidle, чтобы подождать завершения сетевой активности
        await page.goto(url, wait_until="networkidle", timeout=45000)
        
        # Эмуляция активности (двигаем мышь и ждем)
        await page.mouse.move(100, 100)
        await asyncio.sleep(2)
        await page.mouse.move(640, 360)
        print(f"[*] {name}: Клик по плееру...")
        await page.mouse.click(640, 360)
        
        # Ждем ссылку дольше
        for i in range(15):
            if stream_url: break
            await asyncio.sleep(1)

        if not stream_url:
            # Сохраняем скриншот, если ничего не нашли
            file_path = f"errors/{name.replace(' ', '_')}.png"
            await page.screenshot(path=file_path)
            print(f"   [?] {name}: Поток не найден. Скриншот сохранен: {file_path}")

    except Exception as e:
        print(f"   [!] {name}: Ошибка: {type(e).__name__}")
    finally:
        await context.close()
    
    return (name, stream_url) if stream_url else None

async def main():
    async with async_playwright() as p:
        print(">>> ЗАПУСК ГРАББЕРА СО СКРИНШОТАМИ <<<\n")
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        
        tasks = [grab_channel(browser, name, url) for name, url in CHANNELS.items()]
        results = await asyncio.gather(*tasks)
        
        await browser.close()
        
        valid = [r for r in results if r]
        if valid:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for n, l in valid: f.write(f'#EXTINF:-1, {n}\n{l}\n')
            print(f"\n>>> Готово! Собрано: {len(valid)}/{len(CHANNELS)}")
        else:
            print("\n>>> Ссылок нет. Проверь папку 'errors/'")

if __name__ == "__main__":
    asyncio.run(main())

