import asyncio
import random
import datetime
from playwright.async_api import async_playwright

# Актуальный список прямых ссылок на страницы каналов (февраль 2024)
CHANNELS = {
    # Федеральные
    "Первый канал": "https://smotrettv.com/tv/public/1003-pervyj-kanal.html",
    "Россия 1": "https://smotrettv.com/tv/public/784-rossija-1.html",
    "Матч ТВ": "https://smotrettv.com/tv/sport/283-match-strana.html",
    "НТВ": "https://smotrettv.com/tv/public/6-ntv.html",
    "Пятый канал": "https://smotrettv.com/tv/public/330-pjatyj-kanal.html",
    "Россия К": "https://smotrettv.com/tv/educational/216-rossija-kultura.html",
    "Россия 24": "https://smotrettv.com/tv/news/217-rossija-24.html",
    "Карусель": "https://smotrettv.com/tv/kids/311-karusel.html",
    "ОТР": "https://smotret.tv",
    "ТВ Центр": "https://smotrettv.com/tv/public/9-tv-centr.html",
    "Рен ТВ": "https://smotrettv.com/tv/public/316-ren-tv.html",
    "Спас": "https://smotrettv.com/tv/public/20-spas.html",
    "СТС": "https://smotrettv.com/tv/entertainment/783-sts.html",
    "Домашний": "https://smotret.tv",
    "ТВ3": "https://smotret.tv",
    "Пятница": "https://smotret.tv",
    "Звезда": "https://smotrettv.com/tv/public/310-zvezda.html",
    "Мир": "https://smotret.tv",
    "ТНТ": "https://smotrettv.com/tv/entertainment/329-tnt.html",
    "Муз ТВ": "https://smotret.tv",
    # Кино и Развлечения
    "Мосфильм. Золотая коллекция": "https://smotrettv.com/tv/kino/737-mosfilm-zolotaja-kollekcija.html",
    "Дом Кино": "https://smotret.tv",
    "Кино ТВ": "https://smotret.tv",
    "НТВ Хит": "https://smotrettv.com/tv/kino/314-ntv-hit.html",
    "Комедия": "https://smotret.tv",
    "Че": "https://smotret.tv",
    "Ю": "https://smotret.tv",
    "Soloviev Live": "https://smotret.tv",
    # Спорт
    "Евроспорт 1": "https://smotrettv.com/tv/sport/1143-evrosport-1.html",
    "Евроспорт 2": "https://smotret.tv",
    "Sport TV (Uz)": "https://smotret.tv",
    "QazSport": "https://smotret.tv",
    # Познавательные и Мировые
    "Euronews": "https://smotret.tv",
    "Viasat History": "https://smotret.tv",
    "Viasat Nature": "https://smotret.tv",
    "Discovery Channel": "https://smotret.tv",
    "National Geographic": "https://smotret.tv",
    # Детские
    "Disney": "https://smotret.tv",
    "Nickelodeon": "https://smotret.tv",
    "Cartoon Network": "https://smotret.tv"
}

USER_AGENT = "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        now_ts = lambda: datetime.datetime.now().strftime("%H:%M:%S")
        print(f"\n[{now_ts()}] >>> Запуск граббера (Статический список 40 каналов)...")
        
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 450, 'height': 900},
            is_mobile=True,
            has_touch=True
        )
        page = await context.new_page()
        
        # Маскировка
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Блокировка рекламы и картинок для ускорения
        await page.route("**/*.{png,jpg,jpeg,gif,webp,svg}", lambda route: route.abort())

        playlist_results = []
        total = len(CHANNELS)

        for counter, (name, url) in enumerate(CHANNELS.items(), 1):
            ts = now_ts()
            print(f"[{ts}] [{counter}/{total}] Граббинг: {name}")
            current_stream = None

            async def catch_m3u8(request):
                nonlocal current_stream
                u = request.url
                if ".m3u8" in u and len(u) > 50:
                    if not any(x in u for x in ["/ads/", "track", "pixel", "telemetree"]):
                        if not current_stream:
                            current_stream = u
                            print(f"   [+] Поток найден!")

            page.on("request", catch_m3u8)
            
            try:
                # Переход на страницу канала
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(8)
                
                # Клик по плееру
                await page.mouse.click(225, 350)
                await asyncio.sleep(6)
                
                if current_stream:
                    playlist_results.append((name, current_stream))
                else:
                    # Вторая попытка клика чуть ниже (если кнопка Play смещена)
                    await page.mouse.click(225, 450)
                    await asyncio.sleep(4)
                    if current_stream:
                        playlist_results.append((name, current_stream))
            except:
                print(f"   [!] Ошибка загрузки")
            
            page.remove_listener("request", catch_m3u8)
            await asyncio.sleep(random.uniform(1, 2))

        if playlist_results:
            with open("playlist.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for n, l in playlist_results:
                    f.write(f'#EXTINF:-1, {n}\n{l}|Referer=https://smotrettv.com{USER_AGENT}\n')
            print(f"\n[{now_ts()}] ГОТОВО! Собрано каналов: {len(playlist_results)}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())






