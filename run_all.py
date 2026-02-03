import asyncio
import random
import grabber  # ваш файл
from playwright.async_api import async_playwright

# 1. Загружаем все каналы (как в прошлый раз)
import requests
from bs4 import BeautifulSoup

def get_full_list():
    r = requests.get("https://smotrettv.com", headers={"User-Agent": grabber.USER_AGENT})
    soup = BeautifulSoup(r.text, 'html.parser')
    return {a.text.strip(): a['href'] for a in soup.select('a[href*=".html"]') if a.text.strip()}

grabber.CHANNELS = get_full_list()

# 2. ХАК: Увеличиваем паузы, не меняя код grabber.py
# Мы подменяем функцию asyncio.sleep на нашу, которая ждет дольше
original_sleep = asyncio.sleep
async def smart_sleep(delay):
    # Если скрипт хочет ждать 1-10 сек, заставляем его ждать чуть дольше для стабильности
    new_delay = delay + 5 if delay < 20 else delay
    await original_sleep(new_delay)

asyncio.sleep = smart_sleep 

if __name__ == "__main__":
    print(f"[*] Начинаю сбор {len(grabber.CHANNELS)} каналов...")
    asyncio.run(grabber.get_tokens_and_make_playlist())
