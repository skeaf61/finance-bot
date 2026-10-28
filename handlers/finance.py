 # Логика FSM (ввод расходов и доходов)
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
# Импортируем функцию добавления в БД из нашего соседнего модуля
from database.db import add_transaction 

router = Router()

CATEGORIES = {
    "expense": {
        "🍏 Питание": "Питание", 
        "👕 Одежда": "Одежда", 
        "🎬 Развлечения": "Развлечения",
        "⛽ Топливо": "Топливо", 
        "🔧 Обслуживание": "Обслуживание машины",
        "🎁 Подарки": "Подарки",
        "📉 Долги (выплата)": "Погашение долгов", 
        "🔄 Регулярные": "Регулярные платежи",
        "📦 Прочее": "Прочее"
    },
    "income": {
        "💰 Зарплата": "Зарплата",
        "📈 Долги (возврат)": "Возврат долгов",
        "💼 Подработка": "Подработка"
    }
}

class FinanceStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_date_choice = State()
    waiting_for_custom_date = State()
    waiting_for_category = State()

@router.message(Command("expense", "income"))
async def start_finance_entry(message: types.Message, state: FSMContext):
    t_type = "expense" if "expense" in message.text else "income"
    await state.update_data(type=t_type)
    
    op_name = "РАСХОД" if t_type == "expense" else "ДОХОД"
    await message.answer(f"Введите сумму операции ({op_name}) числом:")
    await state.set_state(FinanceStates.waiting_for_amount)

@router.message(FinanceStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    amount_text = message.text.replace(",", ".")
    try:
        amount = float(amount_text)
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число больше нуля:")
        return

    await state.update_data(amount=amount)
    
    today = datetime.now().strftime("%d.%m")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d.%m")
    
    kb = InlineKeyboardBuilder()
    kb.button(text=f"Сегодня ({today})", callback_data="date_today")
    kb.button(text=f"Вчера ({yesterday})", callback_data="date_yesterday")
    kb.button(text="Другой день 🗓️", callback_data="date_custom")
    kb.button(text="❌ Отмена", callback_data="cancel_action")
    kb.adjust(2, 1, 1)
    
    await message.answer(f"Сумма: {amount} руб.\nКогда была совершена операция?", reply_markup=kb.as_markup())
    await state.set_state(FinanceStates.waiting_for_date_choice)

@router.callback_query(FinanceStates.waiting_for_date_choice, F.data.startswith("date_"))
async def process_date_choice(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "date_custom":
        await callback.message.edit_text("Введите дату в формате ДД.ММ (например, 15.10):")
        await state.set_state(FinanceStates.waiting_for_custom_date)
        return

    chosen_date = datetime.now().strftime("%Y-%m-%d") if callback.data == "date_today" else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    await state.update_data(date=chosen_date)
    await ask_category(callback.message, state)

@router.message(FinanceStates.waiting_for_custom_date)
async def process_custom_date(message: types.Message, state: FSMContext):
    try:
        parsed_date = datetime.strptime(message.text, "%d.%m")
        chosen_date = parsed_date.replace(year=datetime.now().year).strftime("%Y-%m-%d")
    except ValueError:
        await message.answer("Неверный формат! Напишите дату в формате ДД.ММ (например, 25.10):")
        return

    await state.update_data(date=chosen_date)
    await ask_category(message, state)

async def ask_category(message: types.Message, state: FSMContext):
    data = await state.get_data()
    t_type = data["type"]
    
    kb = InlineKeyboardBuilder()
    for btn_text in CATEGORIES[t_type].keys():
        kb.button(text=btn_text, callback_data=f"cat_{btn_text}")
    kb.button(text="❌ Отмена", callback_data="cancel_action")
    kb.adjust(2)
    
    text = "Выберите категорию расходов:" if t_type == "expense" else "Выберите категорию доходов:"
    if message.from_user.is_bot:
        await message.edit_text(text, reply_markup=kb.as_markup())
    else:
        await message.answer(text, reply_markup=kb.as_markup())
    await state.set_state(FinanceStates.waiting_for_category)

@router.callback_query(FinanceStates.waiting_for_category, F.data.startswith("cat_"))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    category_btn = callback.data.replace("cat_", "")
    user_data = await state.get_data()
    
    t_type = user_data["type"]
    amount = user_data["amount"]
    date = user_data["date"]
    db_category = CATEGORIES[t_type][category_btn]
    
    # Вызываем функцию сохранения в БД
    table = "expenses" if t_type == "expense" else "incomes"
    transaction_id = add_transaction(table, callback.from_user.id, date, db_category, amount)
    
    f_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    
    await callback.message.edit_text(
        f"✅ Успешно записано!\n\n"
        f"🆔 **ID операции:** #{transaction_id}\n"
        f"Тип: {'Расход' if t_type=='expense' else 'Доход'}\n"
        f"Сумма: {amount} руб.\n"
        f"Дата: {f_date}\n"
        f"Категория: {db_category}",
        parse_mode="Markdown"
    )
    await state.clear()