import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import openai
import nest_asyncio

# Дозволяємо повторне використання активного циклу подій
nest_asyncio.apply()

# Ініціалізація OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY не встановлено!")

# Ініціалізація Telegram Token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не встановлено!")
# Файл для зберігання референсних текстів
REFERENCE_FILE = "reference_texts.txt"

# Створюємо файл, якщо його немає
if not os.path.exists(REFERENCE_FILE):
    with open(REFERENCE_FILE, "w", encoding="utf-8") as f:
        f.write("")

# Завантаження референсних текстів
def load_reference_texts():
    with open(REFERENCE_FILE, "r", encoding="utf-8") as f:
        return f.read().splitlines()

# Додавання тексту до референсної бази
def add_to_reference(text: str):
    reference_texts = load_reference_texts()
    if text not in reference_texts:  # Уникаємо дублювання
        with open(REFERENCE_FILE, "a", encoding="utf-8") as f:
            f.write(text + "\n")
        return "Текст додано до референсної бази."
    else:
        return "Текст уже існує в референсній базі."

# Перевірка тексту через OpenAI API
async def check_plagiarism(user_text: str) -> str:
    try:
        reference_texts = load_reference_texts()
        reference_texts_combined = "\n".join(reference_texts)  # Об'єднуємо референсні тексти для запиту

        # Готуємо запит до OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": (
                    "Ти експерт з виявлення плагіату. Перевір текст користувача на схожість із референсними текстами. "
                    "Якщо текст схожий, поясни, які частини збігаються. Якщо текст унікальний, напиши це."
                )},
                {"role": "user", "content": f"Референсні тексти:\n{reference_texts_combined}"},
                {"role": "user", "content": f"Текст користувача:\n{user_text}"}
            ],
            max_tokens=500,
            temperature=0.3
        )

        # Отримуємо відповідь
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Помилка аналізу: {str(e)}"

# Telegram бот
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Перевірити текст"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Привіт! Надішліть текст для перевірки на плагіат.", reply_markup=reply_markup)

async def check_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text("Перевіряю текст на унікальність, зачекайте...")

    # Перевіряємо текст
    result = await check_plagiarism(user_text)

    # Додаємо текст до бази, якщо він унікальний
    if "унікальний" in result.lower():
        db_update_msg = add_to_reference(user_text)
        await update.message.reply_text(db_update_msg)

    await update.message.reply_text(f"Результат аналізу:\n{result}")

# Основний цикл для Telegram бота
async def telegram_main():
    # Ініціалізація Telegram бота
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Додаємо хендлери для команд та повідомлень
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_text))

    # Запускаємо polling
    await application.run_polling()

if __name__ == "__main__":
    # Використовуємо поточний цикл подій для запуску бота
    asyncio.run(telegram_main())
