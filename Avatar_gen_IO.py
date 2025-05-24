import requests
import json
from typing import List
from urllib.parse import urlencode

#Произошла накладка с Avatargen.IO. API я не смог получить, несмотря на попытки запроса, потому было принято решение изменить подход.
#Я взял файл API_features.json с Гита, ссылка на которую находится на странице с документацией Avatargen.IO, и использовал параметры генерации для своего кода.
#При этом, я использовал другой ресурс - DiceBear. Api свободно можно оттуда получить и там свободно имеются аватары.
#Я корректировал параметры Avatargen.IO под параметры DiceBear (маппинг), дабы они соответствовали по запросу, используя оные со страницы документации DiceBear.
#Ссылка на неё - https://www.dicebear.com/styles/adventurer/#options
#Как-то так... Не знаю, считается это за выполнение, но в момент начала работы я посчитал, что уже поздно что-то менять, да и сама задача мне действительно показалась интересной. Поэтому... Вот...

#Настройки API DiceBear
API_URL = "https://api.dicebear.com/7.x/adventurer/svg"
DEFAULT_PARAMS = {
    "size": 200,
    "radius": 50,
    "backgroundColor": "transparent",
    "flip": "false"
}

#Маппинг параметров
PARAM_MAPPING = {
    "hair_color": {
        "blond": "e5d7a3",
        "chestnut": "6a4e35",
        "dark_blond": "6a4e35",
        "ginger_red": "cb6820",
        "black": "0e0e0e",
        "dark_brown": "6a4e35"
    },
    "skin_tone": {
        "light": "ecad80",
        "pale": "f2d3b1",
        "olive": "9e5622",
        "dark": "763900",
    },
    "glasses": {
        "modern": "variant05",
        "round": "variant04",
        "square": "variant02"
    },
    "hair_style": {
        "male": {
            "regular_front": "short01",
            "crew": "short04",
            "regular_back": "long01",
            "blow_out": "long02",
            "bowl_cut": "short05",
            "bald": "short19",
            "buzz_cut": "short03"
        },
        "female": {
            "pony_tail": "long02",
            "pixie_cut": "short05",
            "bob_cut": "long03",
            "blow_out": "long02",
            "shaggy": "short07",
            "bald": "short19",
            "buzz_cut": "short03"
        }
    }
}

#Загрузка параметров
with open('API_features.json', 'r', encoding='utf-8') as file:
    features = json.load(file)

#Полный перевод на русский
TRANSLATIONS = {
    # Пол
    "male": "Мужской",
    "female": "Женский",
    
    # Цвет волос
    "blond": "Светлые",
    "chestnut": "Коричневые",
    "dark_blond": "Тёмно-русые",
    "ginger_red": "Рыжие",
    "black": "Чёрные",
    "dark_brown": "Тёмно-карие",
    
    # Цвет кожи
    "light": "Светлая",
    "pale": "Бледная",
    "olive": "Светло-коричневая",
    "dark": "Тёмная",
    
    # Очки
    "modern": "Современные",
    "round": "Круглые",
    "square": "Квадратные",
    
    #Волосы
    "regular_front": "Обычная (спереди)",
    "crew": "Ёжик",
    "regular_back": "Обычная (сзади)",
    "blow_out": "Ветреный стиль",
    "bowl_cut": "Горшок",
    "bald": "Лысый",
    "buzz_cut": "Бокс",
    "pony_tail": "Хвостик",
    "pixie_cut": "Пикси",
    "bob_cut": "Каре",
    "shaggy": "Растрёпанные",
    
    # Другое
    "true": "Да",
    "false": "Нет",
    "generic": "Обычный"
}

#Убираем лишние варианты (они читались из файла avatar_gen.IO, потому просто уберу).
def load_filtered_features():
    with open('API_features.json', 'r', encoding='utf-8') as file:
        features = json.load(file)
    
    #Удаляем neutral из skin_tone
    for gender in ["male", "female"]:
        features["API"][gender]["skin_tone"] = [
            tone for tone in features["API"][gender]["skin_tone"] 
            if tone != "neutral"
        ]
    
    #Удаляем afro_blow_out из hair_style
    features["API"]["male"]["hair_style"] = [
        style for style in features["API"]["male"]["hair_style"]
        if style != "afro_blow_out"
    ]
    
    return features

features = load_filtered_features()


def translate(value: str) -> str:
    return TRANSLATIONS.get(value, value)

def show_menu(options: List[str], title: str) -> str:
    print(f"\n{title}:")
    for i, option in enumerate(options, 1):
        print(f"{i}. {translate(option)}")
    while True:
        try:
            choice = int(input("Выберите номер: ")) - 1
            if 0 <= choice < len(options):
                return options[choice]
            print("Пожалуйста, введите номер из списка")
        except ValueError:
            print("Пожалуйста, введите число")

def generate_avatar():
    print("=== Генератор аватаров ===")
    
    #1. Выбор пола
    gender = show_menu(["male", "female"], "Пол")
    params = features["API"][gender]
    options = {**DEFAULT_PARAMS}
    
    #2. Цвет кожи
    options["skinColor"] = PARAM_MAPPING["skin_tone"].get(
        show_menu(params["skin_tone"], "Цвет кожи"), "ecad80"
    )
    
    options["hairColor"] = PARAM_MAPPING["hair_color"].get(
        show_menu(params["hair_color"], "Цвет волос"), "e5d7a3"
    )
    
    #3. Прическа
    hair_style = show_menu(params["hair_style"] + params["alt_hair_style"], "Стиль прически")
    options["hair"] = PARAM_MAPPING["hair_style"][gender].get(hair_style, "short01")
    
    #4. Очки (опционально)
    if show_menu(["true", "false"], "Добавить очки?") == "true":
        glasses_type = show_menu(params["glasses"], "Тип очков")
        options["accessories"] = "glasses"
        options["accessoriesType"] = PARAM_MAPPING["glasses"].get(glasses_type, "variant05")
        options["accessoriesColor"] = options["hairColor"]  # Цвет очков как у волос
    
    #5. Генерация URL и сохранение
    url = f"{API_URL}?{urlencode(options)}"
    print(f"\nФормируем URL: {url}")
    
    response = requests.get(url)
    if response.status_code == 200:
        with open("avatar.svg", "wb") as f:
            f.write(response.content)
        print("\n Аватар успешно создан и сохранён как 'avatar.svg'!")
    else:
        print(f"\n Ошибка генерации! Код: {response.status_code}")

if __name__ == "__main__":
    generate_avatar()
