from aiogram import Router, types, F
from aiogram.filters import Command
from datetime import datetime
from database.db import (
    delete_transaction_by_id_and_table,
    get_monthly_stats,
    get_transaction_by_id,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

class SearchStates(StatesGroup):
    waiting_for_delete_type = State()  # 👈 Ожидаем выбор: расход или доход
    waiting_for_id = State()           # Ожидаем ввод ID
    waiting_for_confirm = State()  # 👈 Добавили шаг подтверждения


router = Router()

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    current_month = datetime.now().strftime("%Y-%m") # ГГГГ-ММ
    
    # 🔥 Запрашиваем расчеты из БД
    total_inc, total_exp, month_categories = get_monthly_stats(user_id, current_month)
    
    text = f"📊 **СТАТИСТИКА ЗА МЕСЯЦ ({current_month}):**\n"
    text += f"💰 Всего доходов: {total_inc} руб.\n"
    text += f"📉 Всего расходов: {total_exp} руб.\n"
    text += f"⚖️ Остаток: {total_inc - total_exp} руб.\n\n"
    
    if month_categories:
        text += "ℹ️ **По категориям:**\n"
        for cat, amt in month_categories:
            text += f"• {cat}: {amt} руб.\n"
    else:
        text += "Записей за этот месяц пока нет."

    await message.answer(text, parse_mode="Markdown")
    

#Функция для удаления расхода/дахода по id
# 1. Пользователь вводит команду, бот предлагает выбор типа операции
@router.message(Command("delete_by_id"))
async def cmd_delete_by_id(message: types.Message, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.button(text="📉 Расход", callback_data="deltype_expenses")
    kb.button(text="💰 Доход", callback_data="deltype_incomes")
    kb.button(text="❌ Отмена", callback_data="cancel_action")
    kb.adjust(2, 1)

    await message.answer(
        "Что именно вы хотите удалить?", 
        reply_markup=kb.as_markup()
    )
    await state.set_state(SearchStates.waiting_for_delete_type)

# 2. Бот ловит выбор типа и запрашивает числовой ID (остается почти без изменений)
@router.callback_query(SearchStates.waiting_for_delete_type, F.data.startswith("deltype_"))
async def process_delete_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    chosen_table = callback.data.replace("deltype_", "")
    await state.update_data(table=chosen_table)
    
    type_name = "РАСХОДА" if chosen_table == "expenses" else "ДОХОДА"
    await callback.message.edit_text(
        f"🔢 Введите ID операции **{type_name}** (просто число без знака #):",
        parse_mode="Markdown"
    )
    await state.set_state(SearchStates.waiting_for_id)

# 3. Бот получает ID текстом, находит запись и просит ПОДТВЕРЖДЕНИЯ
@router.message(SearchStates.waiting_for_id)
async def process_delete_by_id(message: types.Message, state: FSMContext):
    raw_text = message.text.replace("#", "").strip()
    try:
        transaction_id = int(raw_text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректный номер ID (только целое число):")
        return

    user_data = await state.get_data()
    chosen_table = user_data["table"]
    user_id = message.from_user.id
    
    # 🔥 Ищем операцию в базе данных
    transaction = get_transaction_by_id(chosen_table, user_id, transaction_id)

    if not transaction:
        type_label = "расхода" if chosen_table == "expenses" else "дохода"
        await message.answer(f"❌ Запись {type_label} с ID **#{transaction_id}** не найдена или вам не принадлежит.")
        await state.clear()
        return

    # Сохраняем ID операции в память FSM для следующего шага
    await state.update_data(delete_id=transaction_id)

    date, category, amount = transaction
    f_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    type_name = "🔻 Расход" if chosen_table == "expenses" else "🟢 Доход"

    # Строим клавиатуру подтверждения
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, точно удалить", callback_data="confirm_delete_yes")
    kb.button(text="❌ Нет, передумал", callback_data="cancel_action") # использует наш старый хендлер отмены
    kb.adjust(1)

    await message.answer(
        f"❓ **Вы уверены, что хотите удалить эту операцию?**\n\n"
        f"🆔 **ID:** #{transaction_id}\n"
        f"📌 **Тип:** {type_name}\n"
        f"📅 **Дата:** {f_date}\n"
        f"🗂️ **Категория:** {category}\n"
        f"💰 **Сумма:** {amount} руб.",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(SearchStates.waiting_for_confirm)

# 4. Финальное подтверждение удаления
@router.callback_query(SearchStates.waiting_for_confirm, F.data == "confirm_delete_yes")
async def process_confirm_delete(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    user_data = await state.get_data()
    chosen_table = user_data["table"]
    transaction_id = user_data["delete_id"]
    user_id = callback.from_user.id
    
    # 🔥 Вызываем функцию удаления только СЕЙЧАС
    success = delete_transaction_by_id_and_table(chosen_table, user_id, transaction_id)
    await state.clear()

    type_label = "расхода" if chosen_table == "expenses" else "дохода"

    if success:
        await callback.message.edit_text(f"🗑️ Запись {type_label} **#{transaction_id}** успешно удалена.")
    else:
        await callback.message.edit_text("❌ Ошибка при удалении. Возможно, запись уже удалена.")
# ---
