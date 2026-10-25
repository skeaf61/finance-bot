#Команды /start, /cancel
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для учета финансов.\n\n"
        "Используйте меню или команды:\n"
        "/expense — записать расход\n"
        "/income — записать доход\n"
        "/stats - Статистика за месяц\n"
        "/history - Удаление истории"
    )

@router.message(Command("cancel"), ~F.state(None))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Операция отменена. Данные не сохранены.")

@router.callback_query(F.data == "cancel_action")
async def callback_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Операция отменена. Данные не сохранены.")
