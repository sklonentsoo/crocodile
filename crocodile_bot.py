import os
import logging
import random
from typing import Dict
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
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "ВАШ_ТОКЕН_ЗДЕСЬ")

# Словарь для хранения активных игр
games: Dict[int, dict] = {}

# ======================= ВСЕГО СЛОВ =======================
WORDS = [
    "Крокодил", "Собака", "Кошка", "Слон", "Жираф", "Зебра", "Тигр", "Лев", "Пантера", "Гепард",
    "Медведь", "Волк", "Лиса", "Заяц", "Ёж", "Белка", "Обезьяна", "Кенгуру", "Панда", "Носорог",
    "Пицца", "Бургер", "Суп", "Борщ", "Пельмени", "Вареники", "Блинчики", "Оладьи", "Каша", "Рис",
    "Врач", "Учитель", "Полицейский", "Пожарный", "Строитель", "Футбол", "Баскетбол", "Волейбол", "Теннис", "Хоккей",
    "Автомобиль", "Грузовик", "Автобус", "Поезд", "Самолет", "Вертолет", "Корабль", "Лодка", "Велосипед", "Мотоцикл",
    "Солнце", "Луна", "Звезда", "Дождь", "Снег", "Ветер", "Гроза", "Радуга", "Река", "Гора",
    "Дом", "Квартира", "Стол", "Стул", "Кресло", "Диван", "Кровать", "Шкаф", "Телевизор", "Холодильник",
    "Футболка", "Джинсы", "Платье", "Куртка", "Шапка", "Кроссовки", "Сапоги", "Носки", "Шарф", "Перчатки",
    "Телефон", "Компьютер", "Ноутбук", "Планшет", "Наушники", "Клавиатура", "Мышь", "Принтер", "Фотоаппарат", "Дрон",
    "Радость", "Счастье", "Грусть", "Любовь", "Страх", "Гнев", "Удивление", "Спокойствие", "Гордость", "Надежда",
]

random.shuffle(WORDS)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================= КЛАВИАТУРА =======================
def get_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔄 Новое слово", callback_data="new_word")],
        [InlineKeyboardButton("✅ Угадано!", callback_data="guessed")],
        [InlineKeyboardButton("❌ Пропустить", callback_data="skip")],
        [InlineKeyboardButton("🚪 Завершить игру", callback_data="end_game")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🐊 Новая игра", callback_data="menu_new_game")],
        [InlineKeyboardButton("📊 Правила", callback_data="menu_rules")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ======================= ЛОГИКА ИГРЫ =======================
def new_game(chat_id: int, player_id: int, player_name: str) -> dict:
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
    """Команда /start - приветствие"""
    await update.message.reply_text(
        "🐊 *Добро пожаловать в игру КРОКОДИЛ!*\n\n"
        "Правила:\n"
        "• Один игрок показывает слово жестами\n"
        "• Остальные угадывают в чате\n"
        "• Нельзя говорить и показывать на предметы\n\n"
        "*Команды:*\n"
        "/new_game - начать игру\n"
        "/end_game - завершить игру\n"
        "/score - показать счёт\n"
        "/help - помощь",
        parse_mode="Markdown",
        reply_markup=get_menu_keyboard()
    )

async def new_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /new_game - начать игру"""
    chat_id = update.effective_chat.id
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

    if chat_id not in games or not games[chat_id]["active"]:
        if query:
            await query.answer("Игра не активна", show_alert=True)
        else:
            await update.message.reply_text("Нет активной игры.")
        return

    game = games[chat_id]

    results = "🏆 *Итоги игры:*\n"
    for pid, data in sorted(game["players"].items(), key=lambda x: x[1]["score"], reverse=True):
        results += f"• {data['name']}: {data['score']} очков\n"

    if query:
        await query.message.edit_text(results, parse_mode="Markdown")
        await query.answer("Игра завершена")
    else:
        await update.message.reply_text(results, parse_mode="Markdown")

    del games[chat_id]

async def show_score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать текущий счёт"""
    chat_id = update.effective_chat.id

    if chat_id not in games or not games[chat_id]["active"]:
        await update.message.reply_text("Нет активной игры. Начните командой /new_game")
        return

    game = games[chat_id]
    score_text = "📊 *Текущий счёт:*\n"
    for pid, data in game["players"].items():
        score_text += f"• {data['name']}: {data['score']} очков\n"
    
    await update.message.reply_text(score_text, parse_mode="Markdown")

async def guess_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка попыток угадать слово"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    guess = update.message.text.strip().lower()

    if chat_id not in games or not games[chat_id]["active"]:
        return

    game = games[chat_id]
    current_word = game["current_word"].lower()

    # Игрок не может угадывать своё слово
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
            games[chat_id]["last_message_id"] = msg.message_id

        await update.message.reply_text(f"✅ Правильно! Теперь ты показываешь слово.")
    else:
        await update.message.reply_text(f"❌ Неверно! Попробуйте ещё раз.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    data = query.data

    # Обработка главного меню
    if data == "menu_new_game":
        await query.message.delete()
        # Создаём "фейковое" обновление для новой игры
        class FakeMessage:
            def __init__(self, chat, user):
                self.chat = chat
                self.from_user = user
                self.text = "/new_game"
            async def reply_text(self, *args, **kwargs):
                pass
        
        class FakeUpdate:
            def __init__(self, chat, user):
                self.effective_chat = chat
                self.effective_user = user
                self.message = FakeMessage(chat, user)
        
        fake_update = FakeUpdate(update.effective_chat, query.from_user)
        await new_game_command(fake_update, context)
        return
        
    elif data == "menu_rules":
        await query.edit_message_text(
            "📖 *Правила игры Крокодил:*\n\n"
            "1. Водящий показывает слово жестами и мимикой\n"
            "2. Нельзя произносить слова и звуки\n"
            "3. Нельзя показывать на предметы\n"
            "4. Игроки пишут свои версии в чат\n"
            "5. За угаданное слово угадавший получает 1 очко\n\n"
            "🎮 *Команды:*\n"
            "• /new_game - новая игра\n"
            "• /score - счёт\n"
            "• /end_game - завершить",
            parse_mode="Markdown",
            reply_markup=get_menu_keyboard()
        )
        return

    # Проверка активной игры
    if chat_id not in games or not games[chat_id]["active"]:
        await query.edit_message_text("❌ Игра не активна. Нажмите «Новая игра» в меню или используйте /new_game")
        return

    game = games[chat_id]

    if data == "new_word":
        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)
        if not game["words"]:
            await query.edit_message_text("🏁 Слова кончились! Игра завершена.")
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
            await query.edit_message_text("🏁 Слова кончились! Игра завершена.")
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
    if TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        logger.error("❌ Не задан TELEGRAM_BOT_TOKEN!")
        print("Ошибка: Не задан TELEGRAM_BOT_TOKEN!")
        return
    
    logger.info("Бот запускается...")
    
    application = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new_game", new_game_command))
    application.add_handler(CommandHandler("end_game", end_game))
    application.add_handler(CommandHandler("score", show_score))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guess_word))
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Бот успешно запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
