import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, Text
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

OPERATOR_ID = 7630696066  # Замінити на свій Telegram ID
user_operator_map = {}  # ID клієнта -> повідомлення

# Клавіатури
start_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="🚀 Почати")]
])

main_menu = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="🚗 Автоцивілка"), KeyboardButton(text="🌍 Зелена картка")],
    [KeyboardButton(text="🏥 Медичне страхування")]
])

back_button = KeyboardButton(text="🔙 На початок")

share_phone_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="📞 Поділитися номером телефону", request_contact=True)]
])

auto_menu = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="📄 Постійні номера"), KeyboardButton(text="🕘 Транзитні номера")],
    [back_button]
])

duration_menu = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="15 днів"), KeyboardButton(text="1 міс."), KeyboardButton(text="2 міс."), KeyboardButton(text="3 міс.")],
    [back_button]
])

# Стан FSM
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

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Привіт! 👋\nНатисни \"Почати\" щоб дізнатись вартість страхування:", reply_markup=start_keyboard)

@dp.message(Text("🚀 Почати"))
async def on_start_pressed(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    if not user.username:
        await message.answer(
            "⚠️ Оскільки у Вас відсутній username, поділіться, будь ласка, своїм номером телефону, щоб ми могли відповісти:",
            reply_markup=share_phone_keyboard
        )
        return
    await message.answer("Обери вид страхування:", reply_markup=main_menu)

@dp.message(lambda m: m.contact)
async def contact_handler(message: types.Message):
    contact = message.contact
    await bot.send_message(OPERATOR_ID, f"📞 Користувач поділився номером: {contact.phone_number} (ID: {message.from_user.id})")
    await message.answer("✅ Дякую! Номер отримано. Оберіть вид страхування:", reply_markup=main_menu)

@dp.message(Text("🚗 Автоцивілка"))
async def auto_civilka(message: types.Message):
    await message.answer("Оберіть тип номерів:", reply_markup=auto_menu)

@dp.message(Text("📄 Постійні номера"))
async def permanent(message: types.Message, state: FSMContext):
    await state.set_state(AutoForm.number)
    await message.answer("Введіть державний номер авто:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[back_button]]))

@dp.message(Text("🕘 Транзитні номера"))
async def transit(message: types.Message, state: FSMContext):
    await state.set_state(AutoForm.engine)
    await state.update_data(transit=True)
    await message.answer("Введіть об'єм двигуна:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[back_button]]))

@dp.message(Text("🔙 На початок"))
async def go_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Обери вид страхування:", reply_markup=main_menu)

@dp.message(AutoForm.number)
async def get_number(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    await state.update_data(number=message.text)
    await state.set_state(AutoForm.engine)
    await message.answer("Введіть об'єм двигуна:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[back_button]]))

@dp.message(AutoForm.engine)
async def get_engine(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    await state.update_data(engine=message.text)
    await state.set_state(AutoForm.region)
    await message.answer("Вкажіть місце реєстрації:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[back_button]]))

@dp.message(AutoForm.region)
async def get_region(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    await state.update_data(region=message.text)
    await state.set_state(AutoForm.birth)
    await message.answer("Введіть дату народження наймолодшого водія:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[back_button]]))

@dp.message(AutoForm.birth)
async def get_birth(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    await state.update_data(birth=message.text)
    data = await state.get_data()
    if data.get("transit"):
        await state.set_state(AutoForm.term)
        await message.answer("Оберіть термін страхування:", reply_markup=duration_menu)
    else:
        await send_to_operator_and_finish(message, state)

@dp.message(AutoForm.term)
async def get_term(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    await state.update_data(term=message.text)
    await send_to_operator_and_finish(message, state)

async def send_to_operator_and_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name
    text = f"📩 Запит від користувача {username} (ID: {user.id})\n🚘 Запит на Автоцивілку:\n"
    for k, v in data.items():
        text += f"{k.capitalize()}: {v}\n"
    msg = await bot.send_message(OPERATOR_ID, text)
    user_operator_map[msg.message_id] = user.id
    await message.answer("✅ Дані надіслані оператору. За кілька хвилин надішлемо найцікавіші варіанти страхування! 💼")
    await state.clear()

@dp.message(Text("🌍 Зелена картка"))
async def green_card(message: types.Message, state: FSMContext):
    await state.set_state(GreenCard.duration)
    await message.answer("🗓️ Вкажіть на який термін бажаєте (від 15 днів до 12 міс.):", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[back_button]]))

@dp.message(GreenCard.duration)
async def green_card_duration(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    user = message.from_user
    username = f"@{user.username}" if user.username else user.full_name
    msg = await bot.send_message(OPERATOR_ID, f"📩 Запит від користувача {username} (ID: {user.id})\n🟩 Запит на Зелену картку:\nТермін: {message.text}")
    user_operator_map[msg.message_id] = user.id
    await message.answer("✅ Дані надіслані оператору. Чекайте варіанти! 🌍")
    await state.clear()

@dp.message(Text("🏥 Медичне страхування"))
async def medical(message: types.Message, state: FSMContext):
    await state.set_state(TravelInsurance.country)
    await message.answer("🌍 Вкажіть країну поїздки:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[back_button]]))

@dp.message(TravelInsurance.country)
async def get_country(message: types.Message, state: FSMContext):
    if message.text == "🔙 На початок":
        return await go_back(message, state)
    await state.update_data(country=message.text)
    await state.set_state(TravelInsurance.duration)
    await message.answer("🗓️ Вкажіть на який термін бажаєте (від 10 днів до 12 міс.):", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[back_button]]))

@dp.message(TravelInsurance.duration)
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
    await state.clear()

@dp.message(lambda m: m.chat.id == OPERATOR_ID and m.reply_to_message)
async def operator_reply(message: types.Message):
    original_id = message.reply_to_message.message_id
    user_id = user_operator_map.get(original_id)
    if user_id:
        await bot.send_message(user_id, f"📩 Відповідь оператора:\n{message.text}")
    else:
        await message.reply("⚠️ Не вдалося знайти користувача для відповіді.")

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
