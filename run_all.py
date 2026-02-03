import asyncio
import requests
from bs4 import BeautifulSoup
import main_script  # Замените на название вашего файла со скриптом

def get_all_channels():
    print("[*] Сбор списка всех каналов с сайта...")
    url = "https://smotrettv.com"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    all_channels = {}
    # Ищем все ссылки на каналы в сетке сайта
    for link in soup.select('a[href*=".html"]'):
        name = link.text.strip()
        href = link.get('href')
        if name and href.startswith('https://smotrettv.com'):
            all_channels[name] = href
    
    print(f"[+] Найдено каналов: {len(all_channels)}")
    return all_channels

# ГЛАВНЫЙ МОМЕНТ: Подменяем словарь CHANNELS в вашем скрипте перед запуском
main_script.CHANNELS = get_all_channels()

if __name__ == "__main__":
    asyncio.run(main_script.get_tokens_and_make_playlist())

