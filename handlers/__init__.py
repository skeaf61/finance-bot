from aiogram import Router
from .common import router as common_router
from .finance import router as finance_router
from .stats import router as stats_router

# Объединяем все файлы в один главный роутер папки
all_handlers_router = Router()
all_handlers_router.include_routers(common_router, finance_router, stats_router)


