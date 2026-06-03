import os
import logging
import random
import asyncio
from typing import Dict
from datetime import datetime
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
def get_game_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для игры в чате (видят все)"""
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

def get_play_again_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Сыграть ещё' после победы"""
    keyboard = [
        [InlineKeyboardButton("🎮 Сыграть ещё раз", callback_data="play_again")],
        [InlineKeyboardButton("📊 Правила", callback_data="menu_rules")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def reset_timeout(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Сбросить таймер бездействия"""
    if chat_id in games and games[chat_id]["active"]:
        if games[chat_id].get("timeout_task"):
            games[chat_id]["timeout_task"].cancel()
        
        task = asyncio.create_task(timeout_game(context, chat_id))
        games[chat_id]["timeout_task"] = task
        games[chat_id]["last_action"] = datetime.now()

async def timeout_game(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Завершить игру по таймауту"""
    await asyncio.sleep(TIMEOUT_SECONDS)
    
    if chat_id in games and games[chat_id]["active"]:
        game = games[chat_id]
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="⏰ *Прошло 3 минуты бездействия!*\n\n"
                 "Игра автоматически завершена.\n\n"
                 "🎮 Нажмите на кнопку ниже, чтобы начать новую игру!",
            parse_mode="Markdown",
            reply_markup=get_play_again_keyboard()
        )
        
        try:
            await context.bot.send_message(
                chat_id=game["current_player"],
                text="⏰ *Игра завершена из-за бездействия!*",
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
        "game_message_id": None,
    }
    return games[chat_id]

async def update_game_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Обновить сообщение с игрой в чате"""
    if chat_id not in games or not games[chat_id]["active"]:
        return
    
    game = games[chat_id]
    
    text = (
        f"🐊 *ИГРА КРОКОДИЛ*\n\n"
        f"🎭 *Водящий:* {game['current_player_name']}\n"
        f"📖 *Слово:* спрятано 🤫\n\n"
        f"✍️ *Игроки, пишите свои варианты в этот чат!*\n"
        f"🏆 *Кто первый угадает — тот победит!*\n\n"
        f"⏳ *3 минуты бездействия → игра завершится*\n\n"
        f"🔧 *Управление игрой (для водящего):*"
    )
    
    try:
        if game.get("game_message_id"):
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=game["game_message_id"],
                text=text,
                parse_mode="Markdown",
                reply_markup=get_game_keyboard()
            )
        else:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=get_game_keyboard()
            )
            game["game_message_id"] = msg.message_id
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения: {e}")

# ======================= КОМАНДЫ =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🐊 *Игра КРОКОДИЛ*\n\n"
        "Правила:\n"
        "• Водящий показывает слово жестами\n"
        "• Кто первый угадал слово в чате — тот победил!\n"
        "• Водящий получает слово в ЛИЧКУ\n"
        "• *Управление игрой — по кнопкам в чате!*\n"
        "• *3 минуты бездействия → игра завершается*\n\n"
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
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        chat_id = query.message.chat.id
        user_id = query.from_user.id
        user_name = query.from_user.first_name
    else:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name

    if chat_id in games and games[chat_id]["active"]:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Игра уже идёт! Используйте кнопку 'Завершить игру'")
        return

    game = new_game(chat_id, user_id, user_name)
    
    await reset_timeout(context, chat_id)
    
    # Отправляем слово водящему в ЛИЧКУ
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎭 *Ты водящий!*\n\n"
                 f"📖 *Твоё слово:* `{game['current_word']}`\n\n"
                 f"Показывай жестами, остальные угадывают в чате!\n\n"
                 f"Управление игрой — по кнопкам в чате!",
            parse_mode="Markdown"
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ *{user_name}*, слово отправлено тебе в ЛИЧКУ!\n\n🐊 Игра началась!",
            parse_mode="Markdown"
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ *{user_name}*, не могу отправить тебе слово!\nНапиши боту /start в личные сообщения.",
            parse_mode="Markdown"
        )
        del games[chat_id]
        return
    
    # Отправляем игровое сообщение с кнопками в чат
    await update_game_message(context, chat_id)

async def end_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Завершить игру"""
    chat_id = update.effective_chat.id
    query = update.callback_query

    if chat_id not in games or not games[chat_id]["active"]:
        if query:
            await query.answer("Игра не активна")
        else:
            await context.bot.send_message(chat_id=chat_id, text="Нет активной игры.")
        return

    if games[chat_id].get("timeout_task"):
        games[chat_id]["timeout_task"].cancel()

    text = "🏁 *Игра завершена!*\n\n🎮 Нажмите на кнопку ниже, чтобы начать новую игру!"
    
    if query:
        try:
            await query.message.edit_text(text, parse_mode="Markdown", reply_markup=get_play_again_keyboard())
        except:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=get_play_again_keyboard())
        await query.answer("Игра завершена")
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=get_play_again_keyboard())

    del games[chat_id]

async def guess_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка сообщений - ПРОВЕРКА УГАДАЛ ЛИ КТО-ТО"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    message_text = update.message.text.strip()
    
    if message_text.startswith('/'):
        return
    
    if chat_id not in games or not games[chat_id]["active"]:
        return
    
    game = games[chat_id]
    
    await reset_timeout(context, chat_id)
    
    if user_id == game["current_player"]:
        return
    
    current_word = game["current_word"].lower()
    guess = message_text.lower()
    
    if guess == current_word:
        if game.get("timeout_task"):
            game["timeout_task"].cancel()
        
        await update.message.reply_text(
            f"🎉 *ПОБЕДА!* 🎉\n\n"
            f"🏆 *{user_name}* угадал слово!\n"
            f"📖 *Загаданное слово:* {game['current_word']}\n\n"
            f"🐊 Игра завершена!",
            parse_mode="Markdown"
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="🎮 Нажмите на кнопку ниже, чтобы начать новую игру!",
            parse_mode="Markdown",
            reply_markup=get_play_again_keyboard()
        )
        
        try:
            await context.bot.send_message(
                chat_id=game["current_player"],
                text=f"🎉 *Игра завершена!*\n\n🏆 *{user_name}* угадал твоё слово: {game['current_word']}",
                parse_mode="Markdown"
            )
        except:
            pass
        
        del games[chat_id]
        return

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка кнопок в чате"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    chat_id = query.message.chat.id
    data = query.data
    
    # Обработка кнопки "Сыграть ещё раз"
    if data == "play_again":
        await new_game_command(update, context)
        return
    
    # Обработка главного меню
    if data == "menu_new_game":
        await new_game_command(update, context)
        return
    
    if data == "menu_rules":
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
            "/end_game - завершить игру\n\n"
            "🔧 *Кнопки управления в чате:*\n"
            "🔄 - сменить слово\n"
            "✅ - засчитать угаданное\n"
            "❌ - пропустить слово\n"
            "🚪 - завершить игру\n"
            "⏰ - передать ход другому\n\n"
            "⚠️ *Только водящий может нажимать на кнопки!*",
            parse_mode="Markdown",
            reply_markup=get_menu_keyboard()
        )
        return

    # Проверяем, есть ли активная игра
    if chat_id not in games or not games[chat_id]["active"]:
        await query.edit_message_text("❌ Нет активной игры. Начните новую!")
        return
    
    game = games[chat_id]
    
    # Проверяем, что кнопки нажимает ВОДЯЩИЙ
    if user_id != game["current_player"]:
        await query.answer("❌ Только водящий может управлять игрой!", show_alert=True)
        return
    
    await reset_timeout(context, chat_id)
    
    # Обработка действий водящего
    if data == "new_word":
        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)
        
        if not game["words"]:
            await query.edit_message_text("🏁 Слова кончились! Игра завершена.")
            await context.bot.send_message(chat_id=chat_id, text="🎮 Сыграть ещё раз?", reply_markup=get_play_again_keyboard())
            if game.get("timeout_task"):
                game["timeout_task"].cancel()
            del games[chat_id]
            return
        
        game["current_word"] = random.choice(game["words"])
        
        # Обновляем сообщение
        await update_game_message(context, chat_id)
        
        # Уведомление
        await context.bot.send_message(chat_id=chat_id, text="🔄 Водящий заменил слово!")

    elif data == "guessed":
        # Уведомление в чате
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Водящий *{game['current_player_name']}* засчитал угаданное слово!\n📖 Слово будет заменено.",
            parse_mode="Markdown"
        )
        
        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)
        
        if not game["words"]:
            await query.edit_message_text("🏁 Слова кончились! Игра завершена.")
            await context.bot.send_message(chat_id=chat_id, text="🎮 Сыграть ещё раз?", reply_markup=get_play_again_keyboard())
            if game.get("timeout_task"):
                game["timeout_task"].cancel()
            del games[chat_id]
            return
        
        game["current_word"] = random.choice(game["words"])
        
        # Обновляем сообщение
        await update_game_message(context, chat_id)

    elif data == "skip":
        old_word = game["current_word"]
        if old_word in game["words"]:
            game["words"].remove(old_word)
        
        if not game["words"]:
            await query.edit_message_text("🏁 Слова кончились! Игра завершена.")
            await context.bot.send_message(chat_id=chat_id, text="🎮 Сыграть ещё раз?", reply_markup=get_play_again_keyboard())
            if game.get("timeout_task"):
                game["timeout_task"].cancel()
            del games[chat_id]
            return
        
        game["current_word"] = random.choice(game["words"])
        
        await context.bot.send_message(chat_id=chat_id, text="⏩ Водящий пропустил слово!")
        
        # Обновляем сообщение
        await update_game_message(context, chat_id)

    elif data == "pass_turn":
        await context.bot.send_message(
            chat_id=chat_id,
            text="⏰ *Водящий хочет передать ход!*\n\n"
                 "Если хотите стать водящим, напишите в чат: `/take_turn`\n\n"
                 f"*{game['current_player_name']}*, вы остаётесь водящим, пока кто-то не возьмёт ход.",
            parse_mode="Markdown"
        )

    elif data == "end_game":
        if game.get("timeout_task"):
            game["timeout_task"].cancel()
        await query.edit_message_text("🏁 *Игра завершена водящим!*", parse_mode="Markdown")
        await context.bot.send_message(chat_id=chat_id, text="🎮 Сыграть ещё раз?", reply_markup=get_play_again_keyboard())
        del games[chat_id]

async def take_turn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Взять ход себе"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if chat_id not in games or not games[chat_id]["active"]:
        await update.message.reply_text("❌ Нет активной игры.")
        return
    
    game = games[chat_id]
    
    if game["current_player"] == user_id:
        await update.message.reply_text("🤫 Ты уже водящий!")
        return
    
    if game.get("timeout_task"):
        game["timeout_task"].cancel()
    
    # Меняем водящего
    old_player_name = game["current_player_name"]
    game["current_player"] = user_id
    game["current_player_name"] = user_name
    
    # Отправляем слово новому водящему
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎭 *Ты новый водящий!*\n\n"
                 f"📖 *Твоё слово:* `{game['current_word']}`\n\n"
                 f"Показывай жестами! Управление — по кнопкам в чате.",
            parse_mode="Markdown"
        )
        
        await update.message.reply_text(
            f"✅ *{user_name}* стал новым водящим!\n"
            f"Слово отправлено ему в личку.",
            parse_mode="Markdown"
        )
        
        # Обновляем сообщение в чате
        await update_game_message(context, chat_id)
        
        await reset_timeout(context, chat_id)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Не могу отправить слово *{user_name}*!\nНапиши боту /start в личку.",
            parse_mode="Markdown"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)

# ======================= ЗАПУСК =======================
def main() -> None:
    if TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print("❌ Ошибка: Не задан TELEGRAM_BOT_TOKEN!")
        return
    
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new_game", new_game_command))
    application.add_handler(CommandHandler("end_game", end_game_command))
    application.add_handler(CommandHandler("take_turn", take_turn))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guess_word))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("🐊 Бот Крокодил запущен с кнопками в чате!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
