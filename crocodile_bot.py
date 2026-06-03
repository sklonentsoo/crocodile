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

# ======================= СЛОВА =======================
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
        "• Нельзя говорить и показывать на предметы\n"
        "• *Водящий получает слово в ЛИЧНЫЕ СООБЩЕНИЯ!*\n\n"
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
    
    # Отправляем слово В ЛИЧНЫЕ СООБЩЕНИЯ водящему
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎭 *Ты водящий!*\n\nТвоё слово: *{game['current_word']}*\n\nПоказывай его жестами! Игроки должны угадать в чате.\n\nИспользуй кнопки для управления игрой:",
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )
        await update.message.reply_text(f"✅ *{user_name}*, слово отправлено тебе в личные сообщения! 📨\nПоказывай жестами, остальные угадывают в чате.", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение {user_name}: {e}")
        await update.message.reply_text(f"❌ *{user_name}*, не удалось отправить тебе личное сообщение. Убедись, что бот не заблокирован и ты начал с ним диалог (/start у бота в личке).", parse_mode="Markdown")
        del games[chat_id]
        return

    # Отправляем сообщение в чат (без слова!)
    text = (
        f"🐊 *Игра КРОКОДИЛ началась!*\n\n"
        f"🎭 *Водящий:* {user_name}\n"
        f"🤫 *Слово отправлено водящему в личные сообщения!*\n\n"
        f"Игроки, угадывайте слово в чате!"
    )
    message = await update.message.reply_text(
        text, 
        parse_mode="Markdown"
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

    # Уведомляем водящего в ЛС
    current_player_id = game["current_player"]
    try:
        await context.bot.send_message(
            chat_id=current_player_id,
            text=f"🏁 *Игра завершена!*\n\n{results}",
            parse_mode="Markdown"
        )
    except:
        pass

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
                f"🎉 *{user_name}* угадал слово! +1 очко!\n\n🏁 Слова кончились! Игра завершена.",
                parse_mode="Markdown",
            )
            await end_game(update, context)
            return

        game["current_word"] = random.choice(game["words"])
        game["current_player"] = user_id

        # Отправляем НОВОЕ слово новому водящему в ЛС
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎭 *Ты новый водящий!*\n\nТвоё слово: *{game['current_word']}*\n\nПоказывай его жестами! Используй кнопки для управления:",
                parse_mode="Markdown",
                reply_markup=get_keyboard()
            )
            await update.message.reply_text(f"✅ Слово отправлено новому водящему *{user_name}* в личные сообщения!", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение {user_name}: {e}")
            await update.message.reply_text(f"❌ Не удалось отправить слово *{user_name}* в личные сообщения. Игра прервана.", parse_mode="Markdown")
            await end_game(update, context)
            return

        # Обновляем сообщение в чате
        text = (
            f"🎉 *{user_name}* угадал слово! +1 очко 🎉\n\n"
            f"🎭 *Новый водящий:* {user_name}\n"
            f"🤫 *Слово отправлено водящему в личные сообщения!*\n\n"
            f"Игроки, угадывайте!"
        )
        
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=game["last_message_id"],
                text=text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение: {e}")
            msg = await update.message.reply_text(text, parse_mode="Markdown")
            games[chat_id]["last_message_id"] = msg.message_id

        await update.message.reply_text(f"✅ Правильно! *{user_name}* теперь водящий. Слово у него в ЛС.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Неверно! Попробуйте ещё раз.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка кнопок (только для водящего в ЛС)"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data

    # Нужно найти чат, где этот пользователь - водящий
    chat_id = None
    for cid, game in games.items():
        if game["active"] and game["current_player"] == user_id:
            chat_id = cid
            break

    # Если не нашли игру для этого пользователя
    if chat_id is None:
        await query.edit_message_text("❌ У тебя нет активной игры как водящего.")
        return

    game = games[chat_id]

    if data == "new_word":
        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)
        if not game["words"]:
            await query.edit_message_text("🏁 Слова кончились! Игра завершена.")
            # Также уведомить в чате
            for cid, g in games.items():
                if cid == chat_id:
                    try:
                        await context.bot.send_message(chat_id=cid, text="🏁 Слова кончились! Игра завершена.")
                    except:
                        pass
            await end_game(query, context)
            return
        game["current_word"] = random.choice(game["words"])
        text = (
            f"🔄 Слово заменено!\n\n"
            f"📖 *Новое слово:* {game['current_word']}\n\n"
            f"Показывай!"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_keyboard())

    elif data == "guessed":
        game["players"][user_id]["score"] += 1
        
        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)

        if not game["words"]:
            await query.edit_message_text(f"🏁 Слова кончились! Ты получил +1 очко. Игра окончена.")
            await end_game(query, context)
            return

        game["current_word"] = random.choice(game["words"])
        
        text = (
            f"✅ Угадано! +1 очко тебе!\n\n"
            f"📖 *Следующее слово:* {game['current_word']}\n\n"
            f"Показывай!"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_keyboard())
        
        # Уведомление в чате
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Водящий *{game['players'][user_id]['name']}* засчитал угаданное слово! +1 очко ему.\n📖 Слово заменено."
            )
        except:
            pass

    elif data == "skip":
        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)
        if not game["words"]:
            await query.edit_message_text("🏁 Слова кончились! Игра завершена.")
            await end_game(query, context)
            return
        game["current_word"] = random.choice(game["words"])
        text = (
            f"⏩ Слово «{old_word}» пропущено.\n\n"
            f"📖 *Новое слово:* {game['current_word']}"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=get_keyboard())

    elif data == "end_game":
        await end_game(query, context)

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
