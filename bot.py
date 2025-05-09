from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text

import os
from aiogram import Bot

bot = Bot(token=os.getenv("BOT_TOKEN"))
OPERATOR_ID = 7630696066  # Замінити на свій Telegram ID

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

user_operator_map = {}  # ID клієнта -> повідомлення

# Клавіатури
start_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("🚀 Почати"))
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add("🚗 Автоцивілка", "🌍 Зелена картка")
main_menu.add("🏥 Медичне страхування")

back_button = KeyboardButton("🔙 На початок")
share_phone_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("📞 Поділитися номером телефону", request_contact=True)
)

auto_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("📄 Постійні номера"), KeyboardButton("🕘 Транзитні номера")
).add(back_button)

duration_menu = ReplyKeyboardMarkup(resize_keyboard=True)
duration_menu.add("15 днів", "1 міс.", "2 міс.", "3 міс.").add(back_button)

class AutoForm(StatesGroup):
    number = State()
    engine = State()
    region = State()
    birth = State()
    term = State()

class GreenCard(StatesGroup):
    duration = State()

class TravelInsurance(StatesGroup):
    country = State()
    duration = State()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привіт! 👋\nНатисни \"Почати\" щоб дізнатись вартість страхування:", reply_markup=start_keyboard)

@dp.message_handler(Text(equals="🚀 Почати"))
async def on_start_pressed(message: types.Message, state: FSMContext):
    await state.finish()
    user = message.from_user
    if not user.username:
        await message.answer(
            "⚠️ Оскільки у Вас відсутній username, поділіться, будь ласка, своїм номером телефону, щоб ми могли відповісти:",
            reply_markup=share_phone_keyboard
        )
        return
    await message.answer("Обери вид страхування:", reply_markup=main_menu)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def contact_handler(message: types.Message):
    contact = message.contact
    await bot.send_message(OPERATOR_ID, f"📞 Користувач поділився номером: {contact.phone_number} (ID: {message.from_user.id})")
    await message.answer("✅ Дякую! Номер отримано. Оберіть вид страхування:", reply_markup=main_menu)

@dp.message_handler(Text(equals="🚗 Автоцивілка"))
async def auto_civilka(message: types.Message):
    await message.answer("Оберіть тип номерів:", reply_markup=auto_menu)

@dp.message_handler(Text(equals="📄 Постійні номера"))
async def permanent(message: types.Message):
    await message.answer("Введіть державний номер авто:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(back_button))
    await AutoForm.number.set()

@dp.message_handler(Text(equals="🕘 Транзитні номера"))
async def transit(message: types.Message, state: FSMContext):
    await message.answer("Введіть об'єм двигуна:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(back_button))
    await AutoForm.engine.set()
    await state.update_data(transit=True)

@dp.message_handler(Text(equals="🔙 На початок"))
async def go_back(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Обери вид страхування:", reply_markup=main_menu)

@dp.message_handler(state=AutoForm.number)
async def get_number(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    await state.update_data(number=message.text)
    await message.answer("Введіть об'єм двигуна:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(back_button))
    await AutoForm.next()

@dp.message_handler(state=AutoForm.engine)
async def get_engine(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    await state.update_data(engine=message.text)
    await message.answer("Вкажіть місце реєстрації:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(back_button))
    await AutoForm.next()

@dp.message_handler(state=AutoForm.region)
async def get_region(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    await state.update_data(region=message.text)
    await message.answer("Введіть дату народження наймолодшого водія:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(back_button))
    await AutoForm.next()

@dp.message_handler(state=AutoForm.birth)
async def get_birth(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    await state.update_data(birth=message.text)
    data = await state.get_data()
    if data.get('transit'):
        await message.answer("Оберіть термін страхування:", reply_markup=duration_menu)
        await AutoForm.term.set()
    else:
        await send_to_operator_and_finish(message, state)

@dp.message_handler(state=AutoForm.term)
async def get_term(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    await state.update_data(term=message.text)
    await send_to_operator_and_finish(message, state)

async def send_to_operator_and_finish(message, state):
    data = await state.get_data()
    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name
    text = f"📩 Запит від користувача {username} (ID: {user.id})\n"
    text += "🚘 Запит на Автоцивілку:\n"
    for key, val in data.items():
        text += f"{key.capitalize()}: {val}\n"
    msg = await bot.send_message(OPERATOR_ID, text)
    user_operator_map[msg.message_id] = user.id
    await message.answer("✅ Дані надіслані оператору. За кілька хвилин надішлемо найцікавіші варіанти страхування! 💼")
    await state.finish()

@dp.message_handler(Text(equals="🌍 Зелена картка"))
async def green_card(message: types.Message):
    await message.answer("🗓️ Вкажіть на який термін бажаєте (від 15 днів до 12 міс.):", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(back_button))
    await GreenCard.duration.set()

@dp.message_handler(state=GreenCard.duration)
async def green_card_duration(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name
    msg = await bot.send_message(OPERATOR_ID, f"📩 Запит від користувача {username} (ID: {user.id})\n🟩 Запит на Зелену картку:\nТермін: {message.text}")
    user_operator_map[msg.message_id] = user.id
    await message.answer("✅ Дані надіслані оператору. Чекайте варіанти! 🌍")
    await state.finish()

@dp.message_handler(Text(equals="🏥 Медичне страхування"))
async def medical(message: types.Message):
    await message.answer("🌍 Вкажіть країну поїздки:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(back_button))
    await TravelInsurance.country.set()

@dp.message_handler(state=TravelInsurance.country)
async def get_country(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    await state.update_data(country=message.text)
    await message.answer("🗓️ Вкажіть на який термін бажаєте (від 10 днів до 12 міс.):", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(back_button))
    await TravelInsurance.duration.set()

@dp.message_handler(state=TravelInsurance.duration)
async def medical_duration(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    data = await state.get_data()
    country = data.get("country", "Не вказано")
    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name
    msg = await bot.send_message(OPERATOR_ID, f"📩 Запит від користувача {username} (ID: {user.id})\n🏥 Запит на медичне страхування:\nКраїна: {country}\nТермін: {message.text}")
    user_operator_map[msg.message_id] = user.id
    await message.answer("✅ Дані надіслані оператору. Незабаром зв’яжемось! ✈️")
    await state.finish()

@dp.message_handler(lambda m: m.chat.id == OPERATOR_ID and m.reply_to_message)
async def operator_reply(message: types.Message):
    original_id = message.reply_to_message.message_id
    user_id = user_operator_map.get(original_id)
    if user_id:
        await bot.send_message(user_id, f"📩 Відповідь оператора:\n{message.text}")
    else:
        await message.reply("⚠️ Не вдалося знайти користувача для відповіді.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
