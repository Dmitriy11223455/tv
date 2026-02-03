import asyncio
import random
import grabber

# 1. Список реальных браузеров, чтобы сайт не узнал GitHub
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1"
]

# 2. ХАК: Заставляем скрипт менять "личность" перед каждым каналом
original_sleep = asyncio.sleep
async def smart_sleep(seconds):
    # Если это пауза МЕЖДУ каналами (в коде это random.uniform(5, 10))
    if 5 <= seconds <= 10:
        grabber.USER_AGENT = random.choice(USER_AGENTS)
        print(f"[-->] Смена User-Agent для маскировки...")
        await original_sleep(random.uniform(15, 30)) # Увеличиваем паузу, чтобы не забанили
    else:
        await original_sleep(seconds)

asyncio.sleep = smart_sleep

# 3. Подгружаем ВСЕ каналы
import requests
from bs4 import BeautifulSoup

def inject_all():
    r = requests.get("https://smotrettv.com", headers={"User-Agent": random.choice(USER_AGENTS)})
    soup = BeautifulSoup(r.text, 'html.parser')
    links = {a.text.strip(): a['href'] for a in soup.select('a[href*=".html"]') if len(a.text.strip()) > 1}
    grabber.CHANNELS.clear()
    grabber.CHANNELS.update(links)
    print(f"[!] Загружено каналов: {len(grabber.CHANNELS)}")

if __name__ == "__main__":
    inject_all()
    try:
        asyncio.run(grabber.get_tokens_and_make_playlist())
    except Exception as e:
        print(f"Критическая ошибка: {e}")
