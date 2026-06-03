import os
import logging
import random
import asyncio
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ======================= ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ =======================
# Для BotHost.ru переменные задаются в настройках бота
# Локально можно задать через .env или напрямую
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "ВАШ_ТОКЕН_ЗДЕСЬ")
ALLOWED_CHAT_ID = os.environ.get("ALLOWED_CHAT_ID", None)  # Опционально: ограничение по чату

# Словарь для хранения активных игр
games: Dict[int, dict] = {}

# Список слов для игры
WORDS = [
    # ========== ЖИВОТНЫЕ (50) ==========
    "Крокодил", "Собака", "Кошка", "Слон", "Жираф", "Зебра", "Тигр", "Лев", "Пантера", "Гепард",
    "Медведь", "Волк", "Лиса", "Заяц", "Ёж", "Белка", "Обезьяна", "Кенгуру", "Панда", "Носорог",
    "Бегемот", "Кит", "Дельфин", "Акула", "Осьминог", "Медуза", "Черепаха", "Лягушка", "Змея", "Ящерица",
    "Павлин", "Орёл", "Сокол", "Пингвин", "Страус", "Фламинго", "Голубь", "Ворона", "Сорока", "Воробей",
    "Бабочка", "Стрекоза", "Пчела", "Оса", "Муравей", "Паук", "Скорпион", "Краб", "Лобстер", "Омар",
    
    # ========== ЕДА И НАПИТКИ (60) ==========
    "Пицца", "Бургер", "Суп", "Борщ", "Пельмени", "Вареники", "Блинчики", "Оладьи", "Сырники", "Каша",
    "Рис", "Гречка", "Макароны", "Лапша", "Салат", "Оливье", "Селедка под шубой", "Холодец", "Жаркое", "Шашлык",
    "Стейк", "Котлета", "Колбаса", "Сосиска", "Яйцо", "Омлет", "Глазунья", "Торт", "Пирожное", "Мороженое",
    "Конфета", "Шоколад", "Мармелад", "Зефир", "Печенье", "Пряник", "Вафля", "Пончик", "Круассан", "Багет",
    "Яблоко", "Груша", "Апельсин", "Мандарин", "Лимон", "Банан", "Ананас", "Киви", "Манго", "Арбуз",
    "Дыня", "Виноград", "Вишня", "Клубника", "Малина", "Смородина", "Черника", "Клюква", "Кофе", "Чай",
    
    # ========== ПРОФЕССИИ (50) ==========
    "Врач", "Учитель", "Полицейский", "Пожарный", "Строитель", "Архитектор", "Инженер", "Программист", "Дизайнер", "Художник",
    "Музыкант", "Певец", "Танцор", "Актер", "Режиссер", "Сценарист", "Писатель", "Поэт", "Журналист", "Фотограф",
    "Повар", "Официант", "Бармен", "Парикмахер", "Визажист", "Массажист", "Тренер", "Спортсмен", "Футболист", "Хоккеист",
    "Летчик", "Космонавт", "Моряк", "Водитель", "Таксист", "Менеджер", "Бухгалтер", "Юрист", "Судья", "Адвокат",
    "Продавец", "Кассир", "Грузчик", "Курьер", "Охранник", "Уборщик", "Дворник", "Садовник", "Ветеринар", "Стоматолог",
    
    # ========== СПОРТ (40) ==========
    "Футбол", "Баскетбол", "Волейбол", "Теннис", "Хоккей", "Бокс", "Борьба", "Дзюдо", "Карате", "Тхэквондо",
    "Плавание", "Бег", "Прыжки", "Метание", "Гимнастика", "Йога", "Пилатес", "Фитнес", "Бодибилдинг", "Тяжелая атлетика",
    "Лыжи", "Сноуборд", "Коньки", "Фигурное катание", "Биатлон", "Стрельба", "Стрельба из лука", "Фехтование", "Верховая езда", "Гольф",
    "Бильярд", "Боулинг", "Дартс", "Шахматы", "Шашки", "Нарды", "Покер", "Бридж", "Киберспорт", "Скалолазание",
    
    # ========== ТРАНСПОРТ (30) ==========
    "Автомобиль", "Грузовик", "Автобус", "Троллейбус", "Трамвай", "Поезд", "Электричка", "Метро", "Самолет", "Вертолет",
    "Корабль", "Лодка", "Катер", "Яхта", "Подводная лодка", "Танк", "Бронетранспортер", "Мотоцикл", "Велосипед", "Самокат",
    "Электросамокат", "Гироскутер", "Квадроцикл", "Снегоход", "Трактор", "Экскаватор", "Бульдозер", "Кран", "Погрузчик", "Каток",
    
    # ========== ПРИРОДА И ПОГОДА (45) ==========
    "Солнце", "Луна", "Звезда", "Планета", "Комета", "Облако", "Туча", "Дождь", "Снег", "Град",
    "Ветер", "Ураган", "Шторм", "Гроза", "Молния", "Гром", "Радуга", "Туман", "Иней", "Роса",
    "Река", "Озеро", "Море", "Океан", "Водопад", "Гора", "Вулкан", "Пустыня", "Лес", "Джунгли",
    "Поле", "Луг", "Степь", "Болото", "Пляж", "Пещера", "Камень", "Скала", "Песок", "Земля",
    "Цветок", "Дерево", "Трава", "Куст", "Гриб",
    
    # ========== ДОМ И ИНТЕРЬЕР (55) ==========
    "Дом", "Квартира", "Комната", "Кухня", "Ванная", "Туалет", "Прихожая", "Балкон", "Лоджия", "Подвал",
    "Чердак", "Гараж", "Стол", "Стул", "Кресло", "Диван", "Кровать", "Шкаф", "Комод", "Тумба",
    "Полка", "Столовая", "Лампа", "Люстра", "Торшер", "Ковер", "Штора", "Зеркало", "Картина", "Фотография",
    "Телевизор", "Холодильник", "Плита", "Духовка", "Микроволновка", "Посудомоечная машина", "Стиральная машина", "Пылесос", "Утюг", "Фен",
    "Чайник", "Тостер", "Блендер", "Мясорубка", "Электроплита", "Кондиционер", "Обогреватель", "Вентилятор", "Увлажнитель", "Очиститель воздуха",
    "Занавеска", "Подушка", "Одеяло", "Покрывало", "Матрас",
    
    # ========== ОДЕЖДА И ОБУВЬ (60) ==========
    "Футболка", "Майка", "Рубашка", "Блузка", "Свитер", "Джемпер", "Кофта", "Толстовка", "Худи", "Платье",
    "Юбка", "Брюки", "Джинсы", "Шорты", "Бриджи", "Костюм", "Пиджак", "Жакет", "Пальто", "Куртка",
    "Пуховик", "Шуба", "Плащ", "Дождевик", "Носки", "Гольфы", "Колготки", "Рейтузы", "Лосины", "Трико",
    "Шапка", "Кепка", "Бейсболка", "Панама", "Берет", "Платок", "Шарф", "Перчатки", "Варежки", "Ремень",
    "Галстук", "Бабочка", "Запонки", "Часы", "Очки", "Солнцезащитные очки", "Браслет", "Кольцо", "Серьги", "Цепочка",
    "Кроссовки", "Кеды", "Ботинки", "Туфли", "Лодочки", "Сапоги", "Валенки", "Сланцы", "Шлепанцы", "Тапочки",
    
    # ========== ТЕХНИКА И ГАДЖЕТЫ (45) ==========
    "Телефон", "Смартфон", "Планшет", "Ноутбук", "Компьютер", "Монитор", "Клавиатура", "Мышь", "Колонки", "Наушники",
    "Микрофон", "Веб-камера", "Принтер", "Сканер", "Ксерокс", "Факс", "Роутер", "Модем", "Флешка", "Диск",
    "Фотоаппарат", "Видеокамера", "Плеер", "Магнитофон", "Проигрыватель", "Пластинка", "Кассета", "Дискета", "Калькулятор", "Робот",
    "Дрон", "Квадрокоптер", "Пульт", "Батарейка", "Зарядное устройство", "Пауэрбанк", "Провод", "Адаптер", "Трансформатор", "Выключатель",
    "Розетка", "Лампочка", "Светодиод", "Сенсор", "Датчик",
    
    # ========== ШКОЛА И ОФИС (45) ==========
    "Школа", "Университет", "Колледж", "Класс", "Аудитория", "Доска", "Мел", "Указка", "Парта", "Стол",
    "Стул", "Дневник", "Тетрадь", "Блокнот", "Листок", "Ручка", "Карандаш", "Ластик", "Точилка", "Линейка",
    "Циркуль", "Транспортир", "Книга", "Учебник", "Словарь", "Энциклопедия", "Атлас", "Карта", "Глобус", "Пенал",
    "Папка", "Скоросшиватель", "Файл", "Скрепка", "Кнопка", "Скобы", "Степлер", "Дырокол", "Ножницы", "Клей",
    "Скотч", "Корректор", "Маркер", "Фломастер", "Краски",
    
    # ========== ИСКУССТВО (40) ==========
    "Картина", "Рисунок", "Набросок", "Эскиз", "Портрет", "Пейзаж", "Натюрморт", "Абстракция", "Графика", "Живопись",
    "Скульптура", "Статуя", "Бюст", "Барельеф", "Фреска", "Мозаика", "Витраж", "Гравюра", "Эстамп", "Литография",
    "Керамика", "Фарфор", "Стекло", "Хрусталь", "Металл", "Камень", "Дерево", "Бумага", "Холст", "Палитра",
    "Кисть", "Карандаш", "Уголь", "Сангина", "Пастель", "Акварель", "Гуашь", "Масло", "Акрил", "Темпера",
    
    # ========== МУЗЫКА (40) ==========
    "Гитара", "Пианино", "Рояль", "Скрипка", "Виолончель", "Флейта", "Кларнет", "Саксофон", "Труба", "Тромбон",
    "Барабан", "Бубен", "Тамбурин", "Колокольчики", "Ксилофон", "Металлофон", "Гармошка", "Аккордеон", "Баян", "Арфа",
    "Лютня", "Мандолина", "Банджо", "Укулеле", "Балалайка", "Домбра", "Кобыз", "Фортепиано", "Синтезатор", "Электрогитара",
    "Бас-гитара", "Контрабас", "Волынка", "Орган", "Клавесин", "Кастаньеты", "Маракасы", "Шейкер", "Треугольник", "Флексатон",
    
    # ========== ФИЛЬМЫ И ТЕЛЕВИДЕНИЕ (35) ==========
    "Кино", "Фильм", "Сериал", "Мультфильм", "Аниме", "Дорама", "ТВ-шоу", "Ток-шоу", "Новости", "Прогноз погоды",
    "Документалистика", "Реалити-шоу", "КВН", "Юмор", "Комедия", "Трагедия", "Драма", "Триллер", "Хоррор", "Фантастика",
    "Фэнтези", "Детектив", "Боевик", "Экшн", "Приключения", "Мелодрама", "Вестерн", "Нуар", "Артхаус", "Экранизация",
    "Блокбастер", "Кассета", "DVD", "Blu-ray", "Кинопленка",
    
    # ========== ЭМОЦИИ И ЧУВСТВА (40) ==========
    "Радость", "Счастье", "Восторг", "Эйфория", "Удовольствие", "Любовь", "Нежность", "Симпатия", "Уважение", "Восхищение",
    "Грусть", "Печаль", "Тоска", "Скорбь", "Депрессия", "Гнев", "Злость", "Ярость", "Бешенство", "Раздражение",
    "Страх", "Ужас", "Паника", "Тревога", "Беспокойство", "Удивление", "Изумление", "Шок", "Ошеломление", "Интерес",
    "Любопытство", "Стыд", "Вина", "Раскаяние", "Сожаление", "Гордость", "Тщеславие", "Надежда", "Вера", "Спокойствие",
    
    # ========== АБСТРАКТНЫЕ ПОНЯТИЯ (50) ==========
    "Свобода", "Равенство", "Братство", "Справедливость", "Правда", "Истина", "Ложь", "Обман", "Доброта", "Злоба",
    "Красота", "Гармония", "Хаос", "Порядок", "Время", "Пространство", "Энергия", "Сила", "Мощь", "Слабость",
    "Успех", "Удача", "Везучесть", "Неудача", "Богатство", "Бедность", "Здоровье", "Болезнь", "Жизнь", "Смерть",
    "Рождение", "Детство", "Юность", "Зрелость", "Старость", "Память", "Забвение", "Тишина", "Молчание", "Шум",
    "Голод", "Жажда", "Сон", "Бодрствование", "Мир", "Война", "Дружба", "Вражда", "Труд", "Лень",
    
    # ========== ПРАЗДНИКИ (25) ==========
    "Новый год", "Рождество", "Пасха", "День рождения", "Свадьба", "Юбилей", "Выпускной", "День Победы", "8 марта", "23 февраля",
    "День учителя", "День знаний", "Масленица", "Ивана Купала", "Хэллоуин", "День святого Валентина", "День смеха", "День защиты детей", "День независимости", "День города",
    "Ярмарка", "Фестиваль", "Карнавал", "Корпоратив", "Пикник",
    
    # ========== ИСТОРИЧЕСКИЕ ПЕРСОНАЖИ (30) ==========
    "Юлий Цезарь", "Клеопатра", "Наполеон", "Гитлер", "Сталин", "Ленин", "Петр I", "Екатерина II", "Иван Грозный", "Пушкин",
    "Лермонтов", "Толстой", "Достоевский", "Чехов", "Гоголь", "Менделеев", "Ломоносов", "Гагарин", "Терешкова", "Эйнштейн",
    "Ньютон", "Дарвин", "Леонардо да Винчи", "Микеланджело", "Моцарт", "Бетховен", "Чайковский", "Шекспир", "Мартин Лютер Кинг", "Ганди",
    
    # ========== ИГРУШКИ (25) ==========
    "Мяч", "Кукла", "Барби", "Кен", "Пусик", "Медвежонок", "Зайчик", "Собачка", "Конструктор", "Лего",
    "Пазл", "Мозаика", "Домино", "Лото", "Пирамидка", "Юла", "Волчок", "Машинка", "Поезд", "Самолетик",
    "Вертолетик", "Робот", "Трансформер", "Спиннер", "Лизун",
    
    # ========== ЖИЗНЕННЫЕ СИТУАЦИИ (40) ==========
    "Пробуждение", "Завтрак", "Обед", "Ужин", "Учеба", "Работа", "Отдых", "Прогулка", "Шоппинг", "Поездка",
    "Путешествие", "Отпуск", "Выходной", "Будний день", "Понедельник", "Пятница", "Суббота", "Воскресенье", "День", "Ночь",
    "Утро", "Вечер", "Рассвет", "Закат", "Встреча", "Прощание", "Знакомство", "Разговор", "Спор", "Ссора",
    "Примирение", "Прощение", "Поздравление", "Пожелание", "Благодарность", "Извинение", "Просьба", "Предложение", "Согласие", "Отказ",
    
    # ========== КОСМОС (25) ==========
    "Планета", "Звезда", "Солнце", "Луна", "Марс", "Венера", "Юпитер", "Сатурн", "Уран", "Нептун",
    "Галактика", "Млечный путь", "Астероид", "Комета", "Метеорит", "Черная дыра", "Созвездие", "Орбита", "Спутник", "Ракета",
    "Космонавт", "Астронавт", "Скафандр", "Космодром", "МКС",
    
    # ========== СКАЗОЧНЫЕ ПЕРСОНАЖИ (35) ==========
    "Баба-Яга", "Кощей Бессмертный", "Змей Горыныч", "Леший", "Водяной", "Кикимора", "Домовой", "Русалка", "Леший", "Чудо-юдо",
    "Иван-дурак", "Емеля", "Алёша Попович", "Добрыня Никитич", "Илья Муромец", "Золушка", "Белоснежка", "Рапунцель", "Ариэль", "Жасмин",
    "Белль", "Аврора", "Тиана", "Мулан", "Покахонтас", "Красная Шапочка", "Кот в сапогах", "Буратино", "Мальвина", "Пьеро",
    "Арлекин", "Карабас-Барабас", "Дуремар", "Чиполлино", "Незнайка",
]

# Перемешивание при старте игры
random.shuffle(WORDS)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================= ПРОВЕРКА ДОСТУПА =======================
# РАСКОММЕНТИРУЙТЕ ЭТУ ФУНКЦИЮ ТОЛЬКО ЕСЛИ НУЖНО ОГРАНИЧИТЬ КОНКРЕТНЫЙ ЧАТ
def is_allowed_chat(chat_id: int) -> bool:
    """Проверяет, разрешён ли чат (сейчас ВСЕ чаты разрешены)"""
    # Если хотите ограничить конкретным чатом - раскомментируйте следующую строку
    # ALLOWED_CHAT_ID = os.environ.get("ALLOWED_CHAT_ID", None)
    # if ALLOWED_CHAT_ID is None:
    #     return True
    # return str(chat_id) == str(ALLOWED_CHAT_ID)
    
    # Сейчас бот работает во всех чатах (включая личку)
    return True
# ======================= КЛАВИАТУРА =======================
def get_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для управления игрой"""
    keyboard = [
        [InlineKeyboardButton("🔄 Новое слово", callback_data="new_word")],
        [InlineKeyboardButton("✅ Угадано!", callback_data="guessed")],
        [InlineKeyboardButton("❌ Пропустить", callback_data="skip")],
        [InlineKeyboardButton("🚪 Завершить игру", callback_data="end_game")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("🐊 Новая игра", callback_data="menu_new_game")],
        [InlineKeyboardButton("📊 Правила", callback_data="menu_rules")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ======================= ЛОГИКА ИГРЫ =======================
def new_game(chat_id: int, player_id: int, player_name: str) -> dict:
    """Создаёт новую игру"""
    words_copy = WORDS.copy()
    random.shuffle(words_copy)
    games[chat_id] = {
        "words": words_copy,
        "current_word": words_copy[0] if words_copy else "Крокодил",
        "players": {player_id: {"name": player_name, "score": 0}},
        "current_player": player_id,
        "active": True,
        "last_message_id": None,
    }
    return games[chat_id]

# ======================= КОМАНДЫ =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start"""
    chat_id = update.effective_chat.id
    
    if not is_allowed_chat(chat_id):
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    
    await update.message.reply_text(
        "🐊 *Добро пожаложаловать в игру КРОКОДИЛ!*\n\n"
        "Правила простые:\n"
        "• Один игрок показывает слово жестами\n"
        "• Остальные угадывают в чате\n"
        "• Нельзя говорить и показывать предметы\n\n"
        "*Команды:*\n"
        "/new_game - начать игру\n"
        "/end_game - завершить игру\n"
        "/score - показать счёт\n"
        "/help - помощь",
        parse_mode="Markdown",
        reply_markup=get_menu_keyboard()
    )

async def new_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /new_game"""
    chat_id = update.effective_chat.id
    
    if not is_allowed_chat(chat_id):
        return
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if chat_id in games and games[chat_id]["active"]:
        await update.message.reply_text("⚠️ Игра уже идёт! Используйте /end_game для завершения.")
        return

    game = new_game(chat_id, user_id, user_name)

    text = (
        f"🐊 *Игра КРОКОДИЛ началась!*\n\n"
        f"🎭 *Водящий:* {user_name}\n"
        f"📖 *Слово:* ||{game['current_word']}||\n\n"
        f"🤫 Показывайте слово жестами! Игроки пишут ответ в чат."
    )
    message = await update.message.reply_text(
        text, 
        parse_mode="Markdown", 
        reply_markup=get_keyboard()
    )
    games[chat_id]["last_message_id"] = message.message_id

async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Завершить игру"""
    chat_id = update.effective_chat.id
    query = update.callback_query

    if not is_allowed_chat(chat_id):
        if query:
            await query.answer("Доступ запрещён")
        return

    if chat_id not in games or not games[chat_id]["active"]:
        if query:
            await query.answer("Игра не активна", show_alert=True)
        else:
            await update.message.reply_text("Нет активной игры.")
        return

    game = games[chat_id]

    # Итоги
    if game["players"]:
        results = "🏆 *Итоги игры:*\n"
        for pid, data in sorted(game["players"].items(), key=lambda x: x[1]["score"], reverse=True):
            results += f"• {data['name']}: {data['score']} очков\n"
    else:
        results = "Игра завершена без результатов."

    if query:
        await query.message.edit_text(results, parse_mode="Markdown")
        await query.answer("Игра завершена")
    else:
        await update.message.reply_text(results, parse_mode="Markdown")

    del games[chat_id]

async def show_score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать текущий счёт"""
    chat_id = update.effective_chat.id
    
    if not is_allowed_chat(chat_id):
        return

    if chat_id not in games or not games[chat_id]["active"]:
        await update.message.reply_text("Нет активной игры. Начните командой /new_game")
        return

    game = games[chat_id]
    if not game["players"]:
        await update.message.reply_text("Пока нет игроков.")
        return

    score_text = "📊 *Текущий счёт:*\n"
    for pid, data in game["players"].items():
        score_text += f"• {data['name']}: {data['score']} очков\n"
    
    await update.message.reply_text(score_text, parse_mode="Markdown")

async def guess_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка попыток угадать слово"""
    chat_id = update.effective_chat.id
    
    if not is_allowed_chat(chat_id):
        return
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    guess = update.message.text.strip().lower()

    if chat_id not in games or not games[chat_id]["active"]:
        return

    game = games[chat_id]
    current_word = game["current_word"].lower()

    # Игрок не может угадывать своё же слово
    if user_id == game["current_player"]:
        return

    if guess == current_word:
        # Угадал!
        if user_id not in game["players"]:
            game["players"][user_id] = {"name": user_name, "score": 0}
        game["players"][user_id]["score"] += 1

        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)

        if not game["words"]:
            await update.message.reply_text(
                f"🎉 *{user_name}* угадал слово «{old_word}»! +1 очко!\n\n🏁 Слова кончились! Игра завершена.",
                parse_mode="Markdown",
            )
            await end_game(update, context)
            return

        game["current_word"] = random.choice(game["words"])
        game["current_player"] = user_id

        text = (
            f"🎉 *{user_name}* угадал слово «{old_word}»! +1 очко 🎉\n\n"
            f"🎭 *Новый водящий:* {user_name}\n"
            f"📖 *Новое слово:* ||{game['current_word']}||"
        )
        
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=game["last_message_id"],
                text=text,
                parse_mode="Markdown",
                reply_markup=get_keyboard(),
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение: {e}")
            msg = await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_keyboard())
            game["last_message_id"] = msg.message_id

        await update.message.reply_text(f"✅ Правильно! Теперь ты показываешь слово.")
    else:
        await update.message.reply_text(f"❌ Неверно! Попробуйте ещё раз.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    if not is_allowed_chat(chat_id):
        await query.edit_message_text("❌ Доступ запрещён.")
        return
    
    data = query.data

    # Обработка главного меню
    if data == "menu_new_game":
        await query.message.delete()
        # Эмулируем команду /new_game
        fake_update = update
        fake_update.message = query.message
        fake_update.effective_user = query.from_user
        await new_game_command(fake_update, context)
        return
    elif data == "menu_rules":
        await query.edit_message_text(
            "📖 *Правила игры Крокодил:*\n\n"
            "1. Водящий показывает слово жестами и мимикой\n"
            "2. Нельзя произносить слова и звуки\n"
            "3. Нельзя показывать на предметы\n"
            "4. Игроки пишут свои версии в чат\n"
            "5. За угаданное слово угадавший получает 1 очко\n"
            "6. Игра продолжается, пока не кончатся слова\n\n"
            "🎮 *Управление:*\n"
            "• /new_game - новая игра\n"
            "• /score - счёт\n"
            "• /end_game - завершить",
            parse_mode="Markdown",
            reply_markup=get_menu_keyboard()
        )
        return

    # Игровые кнопки
    if chat_id not in games or not games[chat_id]["active"]:
        await query.edit_message_text("Игра не активна. Нажмите «Новая игра» в меню.")
        return

    game = games[chat_id]

    if data == "new_word":
        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)
        if not game["words"]:
            await query.edit_message_text("Слова кончились! Игра завершена.")
            await end_game(update, context)
            return
        game["current_word"] = random.choice(game["words"])
        text = (
            f"🔄 Слово заменено!\n\n"
            f"🎭 *Водящий:* {game['players'][game['current_player']]['name']}\n"
            f"📖 *Новое слово:* ||{game['current_word']}||"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_keyboard())

    elif data == "guessed":
        current_player_id = game["current_player"]
        current_player_name = game["players"][current_player_id]["name"]
        game["players"][current_player_id]["score"] += 1

        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)

        if not game["words"]:
            await query.edit_message_text(f"🏁 Слова кончились! Водящий {current_player_name} получает очко. Игра окончена.")
            await end_game(update, context)
            return

        game["current_word"] = random.choice(game["words"])

        text = (
            f"✅ Угадано! +1 очко водящему *{current_player_name}*\n\n"
            f"📖 *Следующее слово:* ||{game['current_word']}||"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_keyboard())

    elif data == "skip":
        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)
        if not game["words"]:
            await query.edit_message_text("Слова кончились! Игра завершена.")
            await end_game(update, context)
            return
        game["current_word"] = random.choice(game["words"])
        text = (
            f"⏩ Слово «{old_word}» пропущено.\n\n"
            f"📖 *Новое слово:* ||{game['current_word']}||"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_keyboard())

    elif data == "end_game":
        await end_game(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help"""
    await start(update, context)

# ======================= ЗАПУСК =======================
def main() -> None:
    """Запуск бота"""
    if TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        logger.error("❌ Не задан TELEGRAM_BOT_TOKEN!")
        print("Ошибка: Не задан TELEGRAM_BOT_TOKEN!")
        return
    
    logger.info(f"Бот запускается с токеном: {TOKEN[:10]}...")
    
    application = Application.builder().token(TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new_game", new_game_command))
    application.add_handler(CommandHandler("end_game", end_game))
    application.add_handler(CommandHandler("score", show_score))

    # Обработка сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guess_word))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Запуск
    logger.info("Бот успешно запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
