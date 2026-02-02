import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

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

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

async def get_tokens_and_make_playlist():
    playlist_streams = [] 

    async with async_playwright() as p:
        print(">>> Запуск браузера...")
        # Если не ловит в headless=True, поменяй на False, чтобы видеть процесс
        browser = await p.chromium.launch(headless=True)
        
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1280, 'height': 720}
        )
        
        page = await context.new_page()
        # Скрываем следы автоматизации
        await stealth_async(page)

        for name, channel_url in CHANNELS.items():
            print(f"[*] Граббинг: {name}...")
            current_stream_url = None

            # Ловим запросы на уровне КОНТЕКСТА (видит всё внутри фреймов)
            async def handle_request(request):
                nonlocal current_stream_url
                url = request.url
                # Ищем заветный m3u8 с токеном
                if ".m3u8" in url and "token=" in url:
                    current_stream_url = url
                    print(f"   [OK] Ссылка поймана!")

            context.on("request", handle_request)
            
            try:
                # Заходим на страницу
                await page.goto(channel_url, wait_until="networkidle", timeout=60000)
                
                # Ждем чуть-чуть и имитируем активность
                await asyncio.sleep(3)
                # Кликаем примерно в центр плеера, чтобы инициировать поток
                await page.mouse.click(640, 480)
                
                # Ждем появления ссылки 15 сек
                for _ in range(15):
                    if current_stream_url: break
                    await asyncio.sleep(1)

                if current_stream_url:
                    playlist_streams.append((name, current_stream_url))
                else:
                    print(f"   [!] Не удалось вытащить ссылку для {name}")

            except Exception as e:
                print(f"   [!] Ошибка на {name}: {e}")

            # Убираем слушателя перед следующим каналом
            context.remove_listener("request", handle_request)
            await asyncio.sleep(random.uniform(2, 4))

        # Сохранение плейлиста
        if playlist_streams:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for name, link in playlist_streams: 
                    f.write(f'#EXTINF:-1, {name}\n{link}\n')
            print(f"\n>>> Готово! Собрано {len(playlist_streams)} каналов в playlist.m3u")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())
