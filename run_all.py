import asyncio
import requests
from bs4 import BeautifulSoup
import grabber # Импорт вашего основного скрипта

# 1. Собираем ВЕ ПРЯМЫЕ ССЫЛКИ на каналы с главной страницы
def fetch_all_channels():
    print("[!] Собираю полный список каналов...")
    url = "https://smotrettv.com"
    r = requests.get(url, headers={"User-Agent": grabber.USER_AGENT})
    soup = BeautifulSoup(r.text, 'html.parser')
    
    found = {}
    for a in soup.select('a[href*=".html"]'):
        name = a.text.strip()
        link = a['href']
        if name and "smotrettv.com" in link:
            found[name] = link
    return found

# 2. ПОДМЕНА: Заменяем маленький список на полный
full_list = fetch_all_channels()
if full_list:
    grabber.CHANNELS = full_list
    print(f"[OK] Список обновлен: {len(grabber.CHANNELS)} каналов найдено.")

# 3. ЗАПУСК: Вызываем функцию из вашего скрипта
if __name__ == "__main__":
    asyncio.run(grabber.get_tokens_and_make_playlist())


# ГЛАВНЫЙ МОМЕНТ: Подменяем словарь CHANNELS в вашем скрипте перед запуском
main_script.CHANNELS = get_all_channels()

if __name__ == "__main__":
    asyncio.run(main_script.get_tokens_and_make_playlist())

