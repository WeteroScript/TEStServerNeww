#!/usr/bin/env python3
import asyncio
import sys
from config import bot, dp, logger, ADMIN_IDS
from database.file_manager import load_settings

# ✅ ИМПОРТИРУЕМ ВЕСЬ МОДУЛЬ, А НЕ ОТДЕЛЬНЫЕ ПЕРЕМЕННЫЕ!
import services.tasks as tasks
from services.tasks import check_business_loop, promo_auto_loop

from services.auction import auction_update_loop, update_auction_lots, auction_running

from handlers import (
    register_admin_handlers,
    register_user_handlers,
    register_business_handlers,
    register_casino_handlers,
    register_jobs_handlers,
    register_auction_handlers
)

async def main():
    global auction_running
    
    logger.info("🤖 Бот запущен!")
    logger.info(f"👑 Админы: {ADMIN_IDS}")
    
    # ==========================================
    # ===== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ =====
    # ==========================================
    # Сначала специфичные обработчики (с проверкой state)
    register_auction_handlers(dp)   # Ставки на аукцион
    register_jobs_handlers(dp)      # Трейдинг
    register_casino_handlers(dp)    # Казино
    
    # Потом общие обработчики
    register_user_handlers(dp)      # Промокоды и поддержка
    register_admin_handlers(dp)     # Админ-команды
    register_business_handlers(dp)  # Бизнес
    
    try:
        # ==========================================
        # ===== ЗАПУСК БИЗНЕС-ЦИКЛА (АВТО-СБОР) =====
        # ==========================================
        # ✅ ПРАВИЛЬНО: меняем переменную В МОДУЛЕ tasks
        tasks.business_running = True
        tasks.business_check_task = asyncio.create_task(tasks.check_business_loop())
        logger.info("🏢 Цикл проверки бизнесов запущен!")
        
        # ==========================================
        # ===== ЗАПУСК ЦИКЛА АУКЦИОНА =====
        # ==========================================
        auction_running = True
        auction_task = asyncio.create_task(auction_update_loop())
        logger.info("🚗 Цикл обновления аукциона запущен!")
        
        # Инициализируем аукцион
        await update_auction_lots()
        logger.info("🚗 Аукцион инициализирован!")
        
        # ==========================================
        # ===== ЗАПУСК ПРОМОКОДОВ =====
        # ==========================================
        settings = await load_settings()
        if settings.get("promo_auto", False):
            # ✅ ПРАВИЛЬНО: меняем переменную В МОДУЛЕ tasks
            tasks.promo_running = True
            tasks.promo_task = asyncio.create_task(tasks.promo_auto_loop())
            logger.info("📢 Авто-промокоды запущены!")
        
        # ==========================================
        # ===== ЗАПУСК БОТА =====
        # ==========================================
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Завершение работы")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
