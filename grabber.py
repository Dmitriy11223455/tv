import asyncio
import random
from playwright.async_api import async_playwright

CHANNELS = {
    "Первый канал": "https://smotrettv.com/tv/public/1003-pervyj-kanal.html",
    "Россия 1": "https://smotrettv.com/tv/public/784-rossija-1.html",
    "Звезда": "https://smotrettv.com/tv/public/310-zvezda.html",
    "ТНТ": "https://smotrettv.com/tv/entertainment/329-tnt.html",
    "Россия 24": "https://smotrettv.com/tv/news/217-rossija-24.html",
    "СТС": "https://smotrettv.com/tv/entertainment/783-sts.html",
    "НТВ": "https://smotrettv.com/tv/public/6-ntv.html",
    "Рен ТВ": "https://smotrettv.com/tv/public/316-ren-tv.html"
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

async def get_tokens_and_make_playlist():
    playlist_streams = [] 

    async with async_playwright() as p:
        print(">>> Запуск браузера...")
        # Аргументы для обхода детекции автоматизации без лишних библиотек
        browser = await p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox"
        ])
        
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1280, 'height': 720}
        )
        
        page = await context.new_page()

        for name, channel_url in CHANNELS.items():
            print(f"[*] Обработка: {name}...")
            current_stream_url = None

            # Ловим запросы на уровне контекста (важно для iFrame)
            async def handle_request(request):
                nonlocal current_stream_url
                url = request.url
                if ".m3u8" in url and "token=" in url:
                    current_stream_url = url

            context.on("request", handle_request)
            
            try:
                # Переходим на страницу и ждем минимальной загрузки
                await page.goto(channel_url, wait_until="domcontentloaded", timeout=60000)
                
                # Ждем прогрузки скриптов плеера
                await asyncio.sleep(8)
                
                # Имитируем клик в центр плеера для запуска трансляции
                await page.mouse.click(640, 360)
                
                # Ждем поимки ссылки до 12 секунд
                for _ in range(12):
                    if current_stream_url: break
                    await asyncio.sleep(1)

                if current_stream_url:
                    playlist_streams.append((name, current_stream_url))
                    print(f"   [OK] Ссылка получена")
                else:
                    print(f"   [!] Ссылка не найдена")

            except Exception as e:
                print(f"   [!] Ошибка на {name}: {e}")

            context.remove_listener("request", handle_request)
            # Небольшая пауза между каналами, чтобы не забанили
            await asyncio.sleep(random.uniform(2, 4))

        # Запись в файл
        if playlist_streams:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for name, link in playlist_streams: 
                    f.write(f'#EXTINF:-1, {name}\n{link}\n')
            print(f"\n>>> Готово! Собрано каналов: {len(playlist_streams)}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())
