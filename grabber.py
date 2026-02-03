import asyncio
from playwright.async_api import async_playwright

# Твой список каналов
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
    """Функция обработки одного канала с подробными логами"""
    stream_url = None
    context = await browser.new_context(user_agent=USER_AGENT)
    page = await context.new_page()
    
    # Блокируем картинки и шрифты для экономии ресурсов
    await page.route("**/*.{png,jpg,jpeg,css,woff,svg}", lambda route: route.abort())

    async def handle_request(request):
        nonlocal stream_url
        u = request.url
        # Ищем m3u8, игнорируя мусор
        if ".m3u8" in u and not any(x in u for x in ["ads", "yandex", "metrika", "telemetree"]):
            if not stream_url:
                stream_url = u
                print(f"   [!] {name}: УСПЕХ! Ссылка поймана.")

    page.on("request", handle_request)
    
    try:
        print(f"[*] {name}: Захожу на страницу...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        print(f"[*] {name}: Жду прогрузки плеера (7 сек)...")
        await asyncio.sleep(7)
        
        print(f"[*] {name}: Имитирую клик по плееру...")
        await page.mouse.click(640, 360)
        
        print(f"[*] {name}: Проверяю внутренние фреймы (iframe)...")
        for i, frame in enumerate(page.frames):
            try:
                # Пытаемся кликнуть по видео внутри каждого фрейма
                v = await frame.query_selector("video")
                if v:
                    await v.click()
                    print(f"   [-] {name}: Нажал на видео во фрейме #{i}")
            except:
                continue

        # Финальное ожидание ссылки, если еще не поймали
        for sec in range(1, 11):
            if stream_url: break
            if sec % 3 == 0:
                print(f"   [-] {name}: Все еще ищу поток в сетевых запросах ({sec}с)...")
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"[!] {name}: Ошибка выполнения: {type(e).__name__}")
    finally:
        await context.close()
    
    return (name, stream_url) if stream_url else None

async def main():
    async with async_playwright() as p:
        print(">>> ЗАПУСК МНОГОПОТОЧНОГО ГРАББЕРА (8 КАНАЛОВ) <<<")
        print(">>> Весь процесс займет около 30-40 секунд.\n")
        
        browser = await p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        
        # Создаем список задач для одновременного запуска
        tasks = [grab_channel(browser, name, url) for name, url in CHANNELS.items()]
        
        # Запускаем все сразу и ждем завершения
        results = await asyncio.gather(*tasks)
        
        await browser.close()
        
        # Фильтруем успешные результаты
        valid_streams = [r for r in results if r is not None]
        
        if valid_streams:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for name, link in valid_streams:
                    f.write(f'#EXTINF:-1, {name}\n{link}\n')
            print(f"\n>>> РЕЗУЛЬТАТ: Собрано {len(valid_streams)} из {len(CHANNELS)} каналов.")
            print(">>> Файл 'playlist.m3u' готов.")
        else:
            print("\n>>> ОШИБКА: Не удалось получить ни одной ссылки.")

if __name__ == "__main__":
    asyncio.run(main())
