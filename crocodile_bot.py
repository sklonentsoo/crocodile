import os
import logging
import random
import asyncio
from typing import Dict
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ======================= ПЕРЕМЕННЫЕ =======================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "ВАШ_ТОКЕН_ЗДЕСЬ")

# Время ожидания в секундах (3 минуты = 180 секунд)
TIMEOUT_SECONDS = 180

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
]

random.shuffle(WORDS)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================= КЛАВИАТУРА =======================
def get_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для водящего"""
    keyboard = [
        [InlineKeyboardButton("🔄 Новое слово", callback_data="new_word")],
        [InlineKeyboardButton("✅ Угадано", callback_data="guessed")],
        [InlineKeyboardButton("❌ Пропустить", callback_data="skip")],
        [InlineKeyboardButton("🚪 Завершить игру", callback_data="end_game")],
        [InlineKeyboardButton("⏰ Передать ход", callback_data="pass_turn")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("🐊 Новая игра", callback_data="menu_new_game")],
        [InlineKeyboardButton("📊 Правила", callback_data="menu_rules")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def reset_timeout(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Сбросить таймер бездействия"""
    if chat_id in games and games[chat_id]["active"]:
        # Отменяем старый таймер
        if games[chat_id].get("timeout_task"):
            games[chat_id]["timeout_task"].cancel()
        
        # Создаём новый
        task = asyncio.create_task(timeout_game(context, chat_id))
        games[chat_id]["timeout_task"] = task
        games[chat_id]["last_action"] = datetime.now()

async def timeout_game(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Завершить игру по таймауту"""
    await asyncio.sleep(TIMEOUT_SECONDS)
    
    if chat_id in games and games[chat_id]["active"]:
        game = games[chat_id]
        
        # Уведомляем в чате
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ *Прошло 3 минуты бездействия!*\n\n"
                 f"Игра автоматически завершена.\n\n"
                 f"Используйте /new_game чтобы начать заново.",
            parse_mode="Markdown"
        )
        
        # Уведомляем водящего в личку
        try:
            await context.bot.send_message(
                chat_id=game["current_player"],
                text="⏰ *Игра завершена из-за бездействия!*\n\nИспользуйте /new_game чтобы начать заново.",
                parse_mode="Markdown"
            )
        except:
            pass
        
        del games[chat_id]

# ======================= ЛОГИКА ИГРЫ =======================
def new_game(chat_id: int, player_id: int, player_name: str) -> dict:
    words_copy = WORDS.copy()
    random.shuffle(words_copy)
    games[chat_id] = {
        "words": words_copy,
        "current_word": words_copy[0] if words_copy else "Крокодил",
        "current_player": player_id,
        "current_player_name": player_name,
        "active": True,
        "last_action": datetime.now(),
        "timeout_task": None,
    }
    return games[chat_id]

# ======================= КОМАНДЫ =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🐊 *Игра КРОКОДИЛ*\n\n"
        "Правила:\n"
        "• Водящий показывает слово жестами\n"
        "• Кто первый угадал слово в чате — тот победил!\n"
        "• Водящий получает слово в ЛИЧКУ\n"
        "• *3 минуты бездействия → игра автоматически завершается*\n\n"
        "*Команды:*\n"
        "/new_game - начать игру\n"
        "/end_game - завершить игру\n"
        "/help - помощь\n\n"
        "⚠️ *Важно:* добавь бота в группу и сделай АДМИНИСТРАТОРОМ!",
        parse_mode="Markdown",
        reply_markup=get_menu_keyboard()
    )

async def new_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начать новую игру"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    # Проверяем, не идёт ли уже игра
    if chat_id in games and games[chat_id]["active"]:
        await update.message.reply_text("⚠️ Игра уже идёт! Используйте /end_game")
        return

    game = new_game(chat_id, user_id, user_name)
    
    # Запускаем таймер бездействия
    await reset_timeout(context, chat_id)
    
    # Отправляем слово водящему в ЛИЧКУ
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎭 *Ты водящий!*\n\n"
                 f"📖 *Твоё слово:* `{game['current_word']}`\n\n"
                 f"Показывай жестами, остальные угадывают в чате!\n\n"
                 f"Кто первый угадает — тот победит.\n\n"
                 f"*Управление:*\n"
                 f"🔄 Новое слово - сменить слово\n"
                 f"✅ Угадано - засчитать очко\n"
                 f"❌ Пропустить - пропустить слово\n"
                 f"🚪 Завершить игру - закончить игру\n"
                 f"⏰ Передать ход - передать водящим другому\n\n"
                 f"⏳ *Если 3 минуты бездействия - игра закроется*",
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )
        await update.message.reply_text(
            f"✅ *{user_name}*, слово отправлено тебе в ЛИЧКУ!\n\n"
            f"🐊 Игра началась! Кто первый угадает слово в чате — тот победит!\n"
            f"⏳ *3 минуты бездействия → игра завершится*",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ *{user_name}*, не могу отправить тебе слово!\n"
            f"Напиши боту /start в личные сообщения и попробуй снова.",
            parse_mode="Markdown"
        )
        del games[chat_id]
        return

    # Сообщение в чат
    await update.message.reply_text(
        f"🐊 *ИГРА НАЧАЛАСЬ!*\n\n"
        f"🎭 *Водящий:* {user_name}\n"
        f"📖 *Слово отправлено водящему в ЛИЧКУ*\n\n"
        f"✍️ *Пишите свои варианты в этот чат!*\n"
        f"🏆 *Кто первый угадает — тот победит!*\n\n"
        f"⏳ *3 минуты бездействия → игра завершится*",
        parse_mode="Markdown"
    )

async def end_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Завершить игру"""
    chat_id = update.effective_chat.id
    query = update.callback_query

    if chat_id not in games or not games[chat_id]["active"]:
        if query:
            await query.answer("Игра не активна")
        else:
            await update.message.reply_text("Нет активной игры.")
        return

    # Отменяем таймер
    if games[chat_id].get("timeout_task"):
        games[chat_id]["timeout_task"].cancel()

    if query:
        await query.message.edit_text("🏁 *Игра завершена!*", parse_mode="Markdown")
        await query.answer("Игра завершена")
    else:
        await update.message.reply_text("🏁 *Игра завершена!*", parse_mode="Markdown")

    del games[chat_id]

async def pass_turn(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, current_player_id: int) -> None:
    """Передать ход другому игроку"""
    game = games[chat_id]
    
    # Ищем другого игрока в чате (сложно без списка участников)
    # Просто выбираем случайного из players, если есть
    players = list(game.keys())
    # Простая реализация - берём первого попавшегося (кроме текущего)
    # В реальной игре нужно собрать список участников
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="⚠️ Функция передачи хода требует списка участников.\n"
             "Пока что используйте /end_game и начните новую игру с другим водящим.",
        parse_mode="Markdown"
    )

async def guess_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка сообщений - ПРОВЕРКА УГАДАЛ ЛИ КТО-ТО"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    message_text = update.message.text.strip()
    
    # Игнорируем команды
    if message_text.startswith('/'):
        return
    
    # Проверяем, есть ли активная игра
    if chat_id not in games or not games[chat_id]["active"]:
        return
    
    game = games[chat_id]
    
    # Обновляем время последнего действия при любом сообщении в чате
    await reset_timeout(context, chat_id)
    
    # Водящий не может угадывать своё слово (просто игнорируем)
    if user_id == game["current_player"]:
        return
    
    current_word = game["current_word"].lower()
    guess = message_text.lower()
    
    # Если угадал
    if guess == current_word:
        # Отменяем таймер
        if game.get("timeout_task"):
            game["timeout_task"].cancel()
        
        # ПОБЕДА!
        await update.message.reply_text(
            f"🎉 *ПОБЕДА!* 🎉\n\n"
            f"🏆 *{user_name}* угадал слово!\n"
            f"📖 *Загаданное слово:* {game['current_word']}\n\n"
            f"🐊 Игра завершена!",
            parse_mode="Markdown"
        )
        
        # Уведомляем водящего в личку
        try:
            await context.bot.send_message(
                chat_id=game["current_player"],
                text=f"🎉 *Игра завершена!*\n\n"
                     f"🏆 *{user_name}* угадал твоё слово: {game['current_word']}\n\n"
                     f"Ты отлично показал! 🐊",
                parse_mode="Markdown"
            )
        except:
            pass
        
        # Завершаем игру
        del games[chat_id]
        return
    
    # Не угадал - НИЧЕГО НЕ ПИШЕМ

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Кнопки для водящего в личке"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data

    # Ищем игру где этот пользователь - водящий
    chat_id = None
    for cid, game in games.items():
        if game["active"] and game["current_player"] == user_id:
            chat_id = cid
            break

    if chat_id is None:
        await query.edit_message_text("❌ У тебя нет активной игры.")
        return

    game = games[chat_id]
    
    # Обновляем таймер при любом действии водящего
    await reset_timeout(context, chat_id)

    if data == "new_word":
        # Сменить слово
        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)
        
        if not game["words"]:
            await query.edit_message_text("🏁 Слова кончились! Игра завершена.")
            await context.bot.send_message(chat_id=chat_id, text="🏁 Слова кончились! Игра завершена.")
            if game.get("timeout_task"):
                game["timeout_task"].cancel()
            del games[chat_id]
            return
        
        game["current_word"] = random.choice(game["words"])
        await query.edit_message_text(
            f"🔄 *Слово заменено!*\n\n"
            f"📖 *Новое слово:* `{game['current_word']}`\n\n"
            f"Показывай!",
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )
        
        # Уведомление в чате
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🔄 Водящий заменил слово!"
        )

    elif data == "guessed":
        # Засчитать угаданное
        await query.edit_message_text(
            f"✅ *Угадано!*\n\n"
            f"📖 *Следующее слово:* `{game['current_word']}`\n\n"
            f"Показывай!",
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )
        
        # Уведомление в чате
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Водящий засчитал угаданное слово!"
        )

    elif data == "skip":
        # Пропустить слово
        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)
        
        if not game["words"]:
            await query.edit_message_text("🏁 Слова кончились! Игра завершена.")
            await context.bot.send_message(chat_id=chat_id, text="🏁 Слова кончились! Игра завершена.")
            if game.get("timeout_task"):
                game["timeout_task"].cancel()
            del games[chat_id]
            return
        
        game["current_word"] = random.choice(game["words"])
        await query.edit_message_text(
            f"⏩ *Слово пропущено!*\n\n"
            f"📖 *Новое слово:* `{game['current_word']}`",
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )
        
        # Уведомление в чате
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏩ Водящий пропустил слово!"
        )

    elif data == "pass_turn":
        # Передать ход
        await query.edit_message_text(
            f"⏰ *Передача хода*\n\n"
            f"Чтобы передать ход другому игроку, этот игрок должен написать /take_turn в чате.\n\n"
            f"Тогда он станет новым водящим и получит новое слово в личку.",
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ Водящий хочет передать ход!\n\n"
                 f"Если хотите стать водящим, напишите в чат: /take_turn"
        )

    elif data == "end_game":
        # Завершить игру
        if game.get("timeout_task"):
            game["timeout_task"].cancel()
        await query.edit_message_text("🏁 *Игра завершена!*", parse_mode="Markdown")
        await context.bot.send_message(chat_id=chat_id, text="🏁 *Игра завершена водящим!*", parse_mode="Markdown")
        del games[chat_id]

async def take_turn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Взять ход себе (передача водящего)"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if chat_id not in games or not games[chat_id]["active"]:
        await update.message.reply_text("❌ Нет активной игры.")
        return
    
    game = games[chat_id]
    
    # Проверяем, что игра активна и это не текущий водящий
    if game["current_player"] == user_id:
        await update.message.reply_text("🤫 Ты уже водящий!")
        return
    
    # Отменяем старый таймер
    if game.get("timeout_task"):
        game["timeout_task"].cancel()
    
    # Меняем водящего
    old_word = game["current_word"]
    game["current_player"] = user_id
    game["current_player_name"] = user_name
    
    # Отправляем слово новому водящему
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎭 *Ты новый водящий!*\n\n"
                 f"📖 *Твоё слово:* `{game['current_word']}`\n\n"
                 f"Показывай жестами!",
            parse_mode="Markdown",
            reply_markup=get_keyboard()
        )
        
        await update.message.reply_text(
            f"✅ *{user_name}* стал новым водящим!\n"
            f"Слово отправлено ему в личку.",
            parse_mode="Markdown"
        )
        
        # Запускаем новый таймер
        await reset_timeout(context, chat_id)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Не могу отправить слово *{user_name}*!\n"
            f"Напиши боту /start в личку.",
            parse_mode="Markdown"
        )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Кнопка правил"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🐊 *Правила игры Крокодил:*\n\n"
        "1. Водящий показывает слово жестами и мимикой\n"
        "2. Нельзя произносить слова и звуки\n"
        "3. Нельзя показывать на предметы\n"
        "4. Игроки пишут свои версии в чат\n"
        "5. *Кто первый угадал — тот победил!*\n"
        "6. *3 минуты бездействия → игра завершается*\n\n"
        "🎮 *Команды:*\n"
        "/new_game - начать новую игру\n"
        "/end_game - завершить игру\n"
        "/take_turn - стать водящим\n\n"
        "🔧 *Кнопки водящего (в личке):*\n"
        "🔄 - сменить слово\n"
        "✅ - засчитать угаданное\n"
        "❌ - пропустить слово\n"
        "🚪 - завершить игру\n"
        "⏰ - передать ход другому",
        parse_mode="Markdown",
        reply_markup=get_menu_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)

# ======================= ЗАПУСК =======================
def main() -> None:
    if TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print("❌ Ошибка: Не задан TELEGRAM_BOT_TOKEN!")
        return
    
    application = Application.builder().token(TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new_game", new_game_command))
    application.add_handler(CommandHandler("end_game", end_game_command))
    application.add_handler(CommandHandler("take_turn", take_turn))
    
    # Обработка сообщений (только угадывание)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guess_word))
    
    # Кнопки
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^(new_word|guessed|skip|end_game|pass_turn)$"))
    application.add_handler(CallbackQueryHandler(rules, pattern="^menu_rules$"))
    application.add_handler(CallbackQueryHandler(new_game_command, pattern="^menu_new_game$"))

    print("🐊 Бот Крокодил запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
