
import asyncio
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader, PdfWriter

# Регистрируем шрифт
pdfmetrics.registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))

bot = Bot("7526552209:AAGxuLptYIUeqIGzFsrmmcdXB38JiLFyJto", default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    language = State()
    full_name = State()
    passport = State()
    region = State()
    phone = State()
    app_id = State()

TEXTS = {
    "lang_prompt": {
        "ru": "🇷🇺 Пожалуйста, выберите язык / Iltimos, tilni tanlang:",
        "uz": "🇺🇿 Iltimos, tilni tanlang / Пожалуйста, выберите язык:"
    },
    "full_name": {
        "ru": "📌 Укажите вашу фамилию, имя и отчество полностью",
        "uz": "📌 To'liq ism-sharifingizni kiriting"
    },
    "passport": {
        "ru": "📎 Введите серию и номер паспорта",
        "uz": "📎 Pasport seriyasi va raqamini kiriting"
    },
    "region": {
        "ru": "🏘 Укажите область/город вашего проживания.",
        "uz": "🏘 Yashash hududingizni ko'rsating (viloyat/shahar)"
    },
    "phone": {
        "ru": "📞 Введите действующий номер телефона (в формате +998 XX XXX XX XX)",
        "uz": "📞 Telefon raqamingizni kiriting (+998 XX XXX XX XX)"
    },
    "app_id": {
        "ru": "📄 Введите индивидуальный ID вашей заявки",
        "uz": "📄 Arizangizning ID raqamini kiriting"
    },
    "thanks": {
        "ru": "✅ Спасибо! Все данные успешно получены.\nИдёт формирование вашего сертификата участника программы «Жильё 2025».",
        "uz": "✅ Rahmat! Barcha ma'lumotlar olindi.\n«Uy-joy 2025» dasturi ishtirokchisi sertifikati shakllantirilmoqda."
    },
    "doc_generating": {
        "ru": "⏳ Пожалуйста, подождите несколько секунд...",
        "uz": "⏳ Iltimos, bir necha soniya kuting..."
    },
    "pdf_ready": {
        "ru": "📁 Ваш персональный сертификат участника сформирован и зарегистрирован в системе My.Gov.Uz.",
        "uz": "📁 Sertifikatingiz tayyorlandi va My.Gov.Uz tizimida ro'yxatdan o'tkazildi."
    }
}

@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    kb = [[types.KeyboardButton(text="🇷🇺 Русский"), types.KeyboardButton(text="🇺🇿 O'zbek")]]
    await message.answer(TEXTS["lang_prompt"]["ru"], reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(Form.language)

@dp.message(Form.language)
async def language_chosen(message: types.Message, state: FSMContext):
    lang = "ru" if "Рус" in message.text else "uz"
    await state.update_data(lang=lang)
    await message.answer(TEXTS["full_name"][lang], reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.full_name)

@dp.message(Form.full_name)
async def full_name_handler(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    lang = (await state.get_data())["lang"]
    await message.answer(TEXTS["passport"][lang])
    await state.set_state(Form.passport)

@dp.message(Form.passport)
async def passport_handler(message: types.Message, state: FSMContext):
    await state.update_data(passport=message.text)
    lang = (await state.get_data())["lang"]
    await message.answer(TEXTS["region"][lang])
    await state.set_state(Form.region)

@dp.message(Form.region)
async def region_handler(message: types.Message, state: FSMContext):
    await state.update_data(region=message.text)
    lang = (await state.get_data())["lang"]
    await message.answer(TEXTS["phone"][lang])
    await state.set_state(Form.phone)

@dp.message(Form.phone)
async def phone_handler(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    lang = (await state.get_data())["lang"]
    await message.answer(TEXTS["app_id"][lang])
    await state.set_state(Form.app_id)

@dp.message(Form.app_id)
async def app_id_handler(message: types.Message, state: FSMContext):
    await state.update_data(app_id=message.text)
    data = await state.get_data()
    lang = data["lang"]

    intro_msg = await message.answer(TEXTS["thanks"][lang])
    await asyncio.sleep(1)
    progress_msg = await message.answer("📄 Формирование документа [░░░░░░░░░░] 0%")

    for percent in range(1, 101):
        await asyncio.sleep(0.05)
        bar_length = 10
        filled_length = int(bar_length * percent / 100)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        await progress_msg.edit_text(f"📄 Формирование документа [{bar}] {percent}%")

    await progress_msg.edit_text("📄 Формирование документа...")

    filled_pdf = create_filled_pdf(data)
    await intro_msg.delete()
    await progress_msg.delete()

    await message.answer_document(
        FSInputFile(filled_pdf),
        caption=TEXTS["pdf_ready"][lang]
    )

    os.remove(filled_pdf)
    await state.clear()

def create_filled_pdf(data):
    c = canvas.Canvas("overlay.pdf", pagesize=A4)
    c.setFont("DejaVu", 12)

    c.drawString(222, 562, data["full_name"])
    c.drawString(255, 541, data["passport"])
    c.drawString(245, 520, data["region"])
    c.drawString(250, 500, data["phone"])
    c.drawString(340, 481, data["app_id"])
    c.drawString(385, 180, "Шерзод Саиджанович Хидоятов")
    today = datetime.now().strftime("%d      %B ")
    c.drawString(222, 159, today)

    c.save()

    reader = PdfReader("/Users/maratkhanulyyestai/Downloads/sertifikat_final_adjusted_clear.pdf")
    overlay = PdfReader("overlay.pdf")
    writer = PdfWriter()

    page = reader.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)

    output = f"certificate_2025_{data['app_id']}.pdf"
    with open(output, "wb") as f:
        writer.write(f)

    os.remove("overlay.pdf")
    return output

async def main():
    print("✅ Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
