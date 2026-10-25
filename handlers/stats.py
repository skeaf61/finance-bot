from aiogram import Router, types
from aiogram.filters import Command
from datetime import datetime
from database.db import get_monthly_stats

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