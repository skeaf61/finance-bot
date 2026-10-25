# Здесь будет init_db() и функции запросов
import sqlite3
from datetime import datetime

DB_NAME = "finance_bot.db"

def init_db():
    """Создание таблиц при запуске бота"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_transaction(table: str, user_id: int, date: str, category: str, amount: float):
    """Добавление расхода или дохода"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO {table} (user_id, date, category, amount) VALUES (?, ?, ?, ?)",
        (user_id, date, category, amount)
    )
    conn.commit()
    conn.close()

def get_monthly_stats(user_id: int, month_str: str):
    """Получение агрегированных данных за месяц (формат ГГГГ-ММ)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ? AND date LIKE ?", (user_id, f"{month_str}-%"))
    total_exp = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(amount) FROM incomes WHERE user_id = ? AND date LIKE ?", (user_id, f"{month_str}-%"))
    total_inc = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id = ? AND date LIKE ? GROUP BY category", (user_id, f"{month_str}-%"))
    month_categories = cursor.fetchall()
    
    conn.close()
    return total_inc, total_exp, month_categories