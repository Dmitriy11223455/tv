import asyncio
import os
from playwright.async_api import async_playwright

# КОНФИГУРАЦИЯ (добавьте нужные ID каналов из URL сайта)
CHANNELS = {
     "Первый канал": ("https://smotrettv.com/tv/public/1003-pervyj-kanal.html", "1003"),
     "Россия 1": ("https://smotrettv.com/tv/public/784-rossija-1.html", "784"),
     "Звезда": ("https://smotrettv.com/tv/public/310-zvezda.html", "310"),
     "ТНТ": ("https://smotrettv.com/tv/entertainment/329-tnt.html", "329"),
     "Россия 24": ("https://smotrettv.com/tv/news/217-rossija-24.html", "217"),
     "СТС": ("https://smotrettv.com/tv/entertainment/783-sts.html", "783"),
     "НТВ": ("https://smotrettv.com/tv/public/6-ntv.html", "6"),
     "Рен ТВ": ("https://smotrettv.com/tv/public/316-ren-tv.html", "316")
}

STREAM_BASE_URL = "https://server.smotrettv.com/{channel_id}.m3u8?token={token}"

async def get_tokens_and_make_playlist():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        login = os.getenv('LOGIN')
        password = os.getenv('PASSWORD')

        try:
            await page.goto("https://smotrettv.com/login")
            await page.fill('input[name="email"]', login)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Ошибка авторизации: {e}")

        playlist_data = "#EXTM3U\n"
        
        for name, url in CHANNELS.items():
            print(f"Обработка: {name}...")
            current_token = None

            def handle_request(request):
                nonlocal current_token
                if "token=" in request.url:
                    try:
                        current_token = request.url.split("token=")[1].split("&")[0]
                    except:
                        pass

            page.on("request", handle_request)
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(8) 

                if current_token:
                    channel_id = url.split("/")[-1]
                    stream_url = STREAM_BASE_URL.format(channel_id=channel_id, token=current_token)
                    playlist_data += f'#EXTINF:-1, {name}\n{stream_url}\n'
                    print(f"Токен получен.")
            except Exception as e:
                print(f"Ошибка на {name}: {e}")

        with open("playlist_928374hfkj.m3u", "w", encoding="utf-8") as f:
            f.write(playlist_data)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tokens_and_make_playlist())
