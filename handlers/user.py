from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import bot, logger, ADMIN_IDS
from database.file_manager import (
    load_users, save_users, load_inventory, 
    load_promocodes, save_promocodes, load_settings
)
from utils.helpers import (
    check_access, get_default_user, check_subscription, 
    is_function_disabled, is_admin
)
from services.currency import currency_rates

def register_user_handlers(dp):
    
    async def get_main_menu(user_id: str):
        """Главное меню"""
        users = await load_users()
        user = users.get(user_id, get_default_user())
        
        currency_rates.update_rates()
        
        text = (
            f"Главное меню\n\n"
            f"Баланс: {user['money']:,.0f}₽\n"
            f"BRcoins: {user['brcoins']}\n"
            f"BTC: {user['portfolio'].get('BTC', 0)}\n"
            f"WETcoin: {user['portfolio'].get('WETcoin', 0)}\n"
            f"NotCoin: {user['portfolio'].get('NotCoin', 0)}"
        )
        
        keyboard = [
            [InlineKeyboardButton(text="💼 Работы", callback_data="works")],
            [InlineKeyboardButton(text="💎 Донат", callback_data="donate")],
            [InlineKeyboardButton(text="🏆 Форбс", callback_data="forbes")],
            [InlineKeyboardButton(text="🏠 Гараж", callback_data="garage")],
            [InlineKeyboardButton(text="📦 Инвентарь", callback_data="inventory_main")],
            [InlineKeyboardButton(text="🔄 Скупщик", callback_data="buyer")],
            [InlineKeyboardButton(text="🏢 Бизнес", callback_data="business")],
            [InlineKeyboardButton(text="🎰 Казино", callback_data="casino")],
            [InlineKeyboardButton(text="🚗 Аукцион", callback_data="auction")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton(text="🆘 Тех.поддержка", callback_data="support")]
        ]
        
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @dp.message(Command("start"))
    async def start_command(message: types.Message):
        user_id = str(message.from_user.id)
        
        try:
            if not await check_subscription(message.from_user.id):
                await message.answer(
                    "📢 Подпишитесь на канал @WeteroRussia!\n\n"
                    "👉 [Подписаться](https://t.me/+TAhbj7PhoWhhZTQ6)\n\n"
                    "После подписки нажмите /start",
                    parse_mode="Markdown"
                )
                return
            
            users = await load_users()
            
            if user_id not in users:
                users[user_id] = get_default_user()
                await save_users(users)
            
            if not await check_access(message):
                return
            
            text, keyboard = await get_main_menu(user_id)
            await message.answer(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")
    
    @dp.callback_query(F.data == "back_main")
    async def back_main(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            text, keyboard = await get_main_menu(str(callback.from_user.id))
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка в back_main: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    @dp.callback_query(F.data == "stats")
    async def stats_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_9"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            users = await load_users()
            user = users.get(str(callback.from_user.id), get_default_user())
            
            inventory = await load_inventory()
            user_id = str(callback.from_user.id)
            resources_count = len(inventory.get(user_id, []))
            
            business_count = sum(1 for biz in user.get("business", {}).values() if biz.get("owned", False))
            auto_collect_count = sum(1 for biz in user.get("business", {}).values() 
                                    if biz.get("owned", False) and biz.get("auto_collect", False))
            
            text = (
                f"📊 СТАТИСТИКА\n\n"
                f"💰 Баланс: {user['money']:,.0f}₽\n"
                f"💎 BRcoins: {user['brcoins']}\n"
                f"📈 Заработано: {user['total_earned']:,.0f}₽\n"
                f"🤝 Сделок: {user['trades_count']}\n"
                f"👤 Роль: {'Админ' if user['role'] == 'admin' else 'Игрок'}\n"
                f"🚗 Машин: {len(user.get('inventory', []))}\n"
                f"📦 Ресурсов: {resources_count}\n"
                f"⛏️ Попыток: {user['mine_attempts']}/100\n"
                f"🏢 Бизнесов: {business_count}\n"
                f"🤖 Авто-сбор: {auto_collect_count} бизнесов\n\n"
                f"📈 ПОРТФЕЛЬ:\n"
                f"₿ BTC: {user['portfolio'].get('BTC', 0)}/150\n"
                f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}/100\n"
                f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}/5000"
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в stats_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    @dp.callback_query(F.data == "support")
    async def support_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_10"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            await callback.message.edit_text(
                "🆘 ТЕХНИЧЕСКАЯ ПОДДЕРЖКА\n\n"
                "Напишите ваше сообщение для администратора.\n"
                "Мы ответим вам в ближайшее время.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                ])
            )
            await state.set_state("waiting_for_support_message")
            await callback.answer()
        except Exception as e:
            logger.error(f"Ошибка в support_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "garage")
    async def garage_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_4"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if "inventory" not in user or not user["inventory"]:
                await callback.message.edit_text(
                    "🏠 Ваш гараж пуст!\n\n"
                    "💡 Получайте машины через админов или в будущих акциях!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                    ])
                )
                await callback.answer()
                return
            
            keyboard = []
            for i, car in enumerate(user["inventory"]):
                if isinstance(car, dict):
                    car_name = car.get("name", "Неизвестная машина")
                else:
                    car_name = str(car)
                keyboard.append([InlineKeyboardButton(
                    text=f"🚗 {car_name}",
                    callback_data=f"car_{i}"
                )])
            
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
            
            await callback.message.edit_text(
                f"🏠 Ваш гараж ({len(user['inventory'])} машин):",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в garage_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("car_") & ~F.data.startswith("car_sell_"))
    async def car_menu(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            car_index = int(callback.data.split("_")[1])
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if car_index >= len(user["inventory"]):
                await callback.answer("❌ Машина не найдена!", show_alert=True)
                return
            
            car = user["inventory"][car_index]
            
            keyboard = [
                [InlineKeyboardButton(text="💰 Продать (60%)", callback_data=f"car_sell_{car_index}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="garage")]
            ]
            
            await callback.message.edit_text(
                f"🚗 {car['name']}\n"
                f"💰 Стоимость: {car['price']:,.0f}₽\n"
                f"💵 Продажа: {int(car['price'] * 0.6):,.0f}₽ (60%)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except (ValueError, IndexError):
            await callback.answer("❌ Ошибка в данных!")
        except Exception as e:
            logger.error(f"Ошибка в car_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("car_sell_"))
    async def car_sell(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            car_index = int(callback.data.split("_")[2])
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if car_index >= len(user["inventory"]):
                await callback.answer("❌ Машина не найдена!", show_alert=True)
                return
            
            car = user["inventory"][car_index]
            sell_price = int(car["price"] * 0.6)
            
            user["money"] += sell_price
            del user["inventory"][car_index]
            
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"💰 Продано!\n"
                f"🚗 {car['name']}\n"
                f"💳 Получено: {sell_price:,.0f}₽ (60% от цены)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В гараж", callback_data="garage")]
                ])
            )
        except (ValueError, IndexError):
            await callback.answer("❌ Ошибка в данных!")
        except Exception as e:
            logger.error(f"Ошибка в car_sell: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "inventory_main")
    async def inventory_main_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_5"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            inventory = await load_inventory()
            
            if user_id not in inventory or not inventory[user_id]:
                await callback.message.edit_text(
                    "📦 Ваш инвентарь пуст!\nДобывайте ресурсы в шахте или на ферме.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                    ])
                )
                await callback.answer()
                return
            
            from config import MINE_RESOURCES, FARM_RESOURCES
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            resources = {}
            for item in inventory[user_id]:
                resources[item] = resources.get(item, 0) + 1
            
            text = "📦 ВАШ ИНВЕНТАРЬ:\n\n"
            for name, count in resources.items():
                price = 0
                for r in all_resources:
                    if r["name"] == name:
                        price = r["price"]
                        break
                text += f"💎 {name}\n   📦 {count} шт.\n   💰 {price:,.0f}₽ за шт.\n\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в inventory_main_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "forbes")
    async def forbes_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_3"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            keyboard = [
                [InlineKeyboardButton(text="🏆 По деньгам", callback_data="forbes_rich")],
                [InlineKeyboardButton(text="💎 По BRcoins", callback_data="forbes_br")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            await callback.message.edit_text(
                "🏆 Форбс",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в forbes_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "forbes_rich")
    async def forbes_rich(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            users = await load_users()
            sorted_users = sorted(
                users.items(),
                key=lambda x: x[1]["money"],
                reverse=True
            )[:10]
            
            if not sorted_users:
                await callback.answer("Нет данных")
                return
            
            text = "🏆 Топ-10 по деньгам:\n\n"
            for i, (user_id, data) in enumerate(sorted_users, 1):
                try:
                    user = await bot.get_chat(int(user_id))
                    username = user.username or f"User_{user_id[:5]}"
                except:
                    username = f"User_{user_id[:5]}"
                text += f"{i}. @{username} — {data['money']:,.0f}₽\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="forbes")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в forbes_rich: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "forbes_br")
    async def forbes_br(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            users = await load_users()
            sorted_users = sorted(
                users.items(),
                key=lambda x: x[1]["brcoins"],
                reverse=True
            )[:10]
            
            if not sorted_users:
                await callback.answer("Нет данных")
                return
            
            text = "💎 Топ-10 по BRcoins:\n\n"
            for i, (user_id, data) in enumerate(sorted_users, 1):
                try:
                    user = await bot.get_chat(int(user_id))
                    username = user.username or f"User_{user_id[:5]}"
                except:
                    username = f"User_{user_id[:5]}"
                text += f"{i}. @{username} — {data['brcoins']} BRcoins\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="forbes")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в forbes_br: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "donate")
    async def donate_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_2"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            keyboard = [
                [InlineKeyboardButton(text="💳 Купить", callback_data="donate_buy")],
                [InlineKeyboardButton(text="🎫 Промокод", callback_data="promo")],
                [InlineKeyboardButton(text="💰 Баланс", callback_data="donate_balance")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            await callback.message.edit_text(
                "💎 Донат\nКурс: 1₽ = 10 BRcoins\n@weterochina",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в donate_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "donate_buy")
    async def donate_buy(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            await callback.message.edit_text(
                "💳 Обратитесь к @weterochina",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в donate_buy: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "promo")
    async def promo_menu(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            await callback.message.edit_text(
                "🎫 Введите промокод в чат",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в promo_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "donate_balance")
    async def donate_balance(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            users = await load_users()
            user = users.get(str(callback.from_user.id), get_default_user())
            
            await callback.message.edit_text(
                f"💰 Баланс доната\n"
                f"Потрачено: {user['donate_spent']}₽\n"
                f"Получено: {user['donate_received']} BRcoins\n"
                f"Баланс: {user['brcoins']} BRcoins",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в donate_balance: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "buyer")
    async def buyer_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_6"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            inventory = await load_inventory()
            
            if user_id not in inventory or not inventory[user_id]:
                await callback.message.edit_text(
                    "📦 Ваш инвентарь пуст!\nДобывайте ресурсы в шахте или на ферме.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                    ])
                )
                await callback.answer()
                return
            
            from config import MINE_RESOURCES, FARM_RESOURCES
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            resources = {}
            for item in inventory[user_id]:
                resources[item] = resources.get(item, 0) + 1
            
            keyboard = []
            for name, count in resources.items():
                price = 0
                for r in all_resources:
                    if r["name"] == name:
                        price = r["price"]
                        break
                keyboard.append([InlineKeyboardButton(
                    text=f"💎 {name} ({count} шт.) - {price:,.0f}₽",
                    callback_data=f"buyer_resource_{name}"
                )])
            
            keyboard.append([InlineKeyboardButton(text="💰 Продать все", callback_data="buyer_sell_all")])
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
            
            await callback.message.edit_text(
                "🔄 СКУПЩИК\n\nВыберите ресурс для продажи:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в buyer_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("buyer_resource_"))
    async def buyer_resource_menu(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            resource_name = callback.data.replace("buyer_resource_", "")
            
            user_id = str(callback.from_user.id)
            inventory = await load_inventory()
            
            if user_id not in inventory:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return
            
            from config import MINE_RESOURCES, FARM_RESOURCES
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            price = 0
            for r in all_resources:
                if r["name"] == resource_name:
                    price = r["price"]
                    break
            
            if price == 0:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return
            
            count = inventory[user_id].count(resource_name)
            
            keyboard = [
                [InlineKeyboardButton(
                    text=f"💰 Продать 1 шт. ({price:,.0f}₽)",
                    callback_data=f"buyer_sell_one_{resource_name}"
                )],
                [InlineKeyboardButton(
                    text=f"💰 Продать все ({count} шт.)",
                    callback_data=f"buyer_sell_all_{resource_name}"
                )],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="buyer")]
            ]
            
            await callback.message.edit_text(
                f"💎 {resource_name}\n\n"
                f"📦 В наличии: {count} шт.\n"
                f"💰 Цена за шт.: {price:,.0f}₽\n"
                f"💵 Сумма за все: {count * price:,.0f}₽\n\n"
                f"Выберите действие:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в buyer_resource_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("buyer_sell_one_"))
    async def buyer_sell_one(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            resource_name = callback.data.replace("buyer_sell_one_", "")
            
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            inventory = await load_inventory()
            
            if user_id not in inventory or resource_name not in inventory[user_id]:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return
            
            from config import MINE_RESOURCES, FARM_RESOURCES
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            price = 0
            for r in all_resources:
                if r["name"] == resource_name:
                    price = r["price"]
                    break
            
            if price == 0:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return
            
            inventory[user_id].remove(resource_name)
            await save_inventory(inventory)
            
            user["money"] += price
            user["total_earned"] = user.get("total_earned", 0) + price
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"✅ Продано 1 шт. {resource_name}\n"
                f"💰 +{price:,.0f}₽\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 К ресурсам", callback_data="buyer")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в buyer_sell_one: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("buyer_sell_all_"))
    async def buyer_sell_all_resource(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            resource_name = callback.data.replace("buyer_sell_all_", "")
            
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            inventory = await load_inventory()
            
            if user_id not in inventory:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return
            
            from config import MINE_RESOURCES, FARM_RESOURCES
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            price = 0
            for r in all_resources:
                if r["name"] == resource_name:
                    price = r["price"]
                    break
            
            if price == 0:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return
            
            count = inventory[user_id].count(resource_name)
            if count == 0:
                await callback.answer("❌ Нет ресурсов для продажи!", show_alert=True)
                return
            
            total_price = count * price
            
            inventory[user_id] = [item for item in inventory[user_id] if item != resource_name]
            await save_inventory(inventory)
            
            user["money"] += total_price
            user["total_earned"] = user.get("total_earned", 0) + total_price
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"✅ Продано {count} шт. {resource_name}\n"
                f"💰 +{total_price:,.0f}₽\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 К ресурсам", callback_data="buyer")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в buyer_sell_all_resource: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "buyer_sell_all")
    async def buyer_sell_all(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            inventory = await load_inventory()
            
            if user_id not in inventory or not inventory[user_id]:
                await callback.answer("❌ Инвентарь пуст!", show_alert=True)
                return
            
            from config import MINE_RESOURCES, FARM_RESOURCES
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            total_price = 0
            resource_counts = {}
            for item in inventory[user_id]:
                price = 0
                for r in all_resources:
                    if r["name"] == item:
                        price = r["price"]
                        break
                total_price += price
                resource_counts[item] = resource_counts.get(item, 0) + 1
            
            inventory[user_id] = []
            await save_inventory(inventory)
            
            user["money"] += total_price
            user["total_earned"] = user.get("total_earned", 0) + total_price
            users[user_id] = user
            await save_users(users)
            
            resources_text = ""
            for name, count in resource_counts.items():
                resources_text += f"• {name}: {count} шт.\n"
            
            await callback.message.edit_text(
                f"✅ Проданы все ресурсы!\n\n"
                f"📦 Продано:\n{resources_text}\n"
                f"💰 Всего получено: {total_price:,.0f}₽\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В меню", callback_data="back_main")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в buyer_sell_all: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ГЛАВНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ =====
    # ==========================================
    
    @dp.message(F.text, ~F.text.startswith('/'))
    async def handle_promo_and_support(message: types.Message, state: FSMContext):
        """Обрабатывает только промокоды и поддержку"""
        if not await check_access(message):
            return
        
        current_state = await state.get_state()
        
        # ===== КРИТИЧЕСКИ ВАЖНО! =====
        # Если есть активное состояние - НЕ ТРОГАЕМ сообщение!
        # Пусть другие обработчики (аукцион, казино, трейдинг) работают
        if current_state is not None:
            return  # ← ВОТ ЭТА СТРОКА РЕШАЕТ ВСЁ!
        
        # ===== ОБРАБОТКА ПОДДЕРЖКИ =====
        if current_state == "waiting_for_support_message":
            try:
                user_id = str(message.from_user.id)
                users = await load_users()
                user = users.get(user_id, get_default_user())
                
                username = message.from_user.username or f"User_{user_id[:5]}"
                
                support_text = (
                    f"🆘 НОВОЕ ОБРАЩЕНИЕ В ПОДДЕРЖКУ\n\n"
                    f"👤 От: @{username}\n"
                    f"🆔 ID: {user_id}\n"
                    f"💰 Баланс: {user['money']:,.0f}₽\n"
                    f"💎 BRcoins: {user['brcoins']}\n\n"
                    f"📝 Сообщение:\n{message.text}"
                )
                
                sent_to = 0
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(admin_id, support_text)
                        sent_to += 1
                    except Exception as e:
                        logger.warning(f"Не удалось отправить админу {admin_id}: {e}")
                
                await state.clear()
                
                if sent_to > 0:
                    await message.answer(
                        "✅ Ваше сообщение отправлено администратору!\n"
                        "Мы свяжемся с вами в ближайшее время.",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 В меню", callback_data="back_main")]
                        ])
                    )
                else:
                    await message.answer(
                        "❌ Не удалось отправить сообщение. Попробуйте позже.",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 В меню", callback_data="back_main")]
                        ])
                    )
            except Exception as e:
                logger.error(f"Ошибка в process_support_message: {e}")
                await state.clear()
                await message.answer("⚠️ Произошла ошибка! Попробуйте позже.")
            return
        
        # ===== ОБРАБОТКА ПРОМОКОДОВ =====
        # Только если НЕТ активного состояния
        try:
            user_id = str(message.from_user.id)
            users = await load_users()
            user = users.get(user_id)
            
            if not user:
                return
            
            promocodes = await load_promocodes()
            code = message.text.upper().strip()
            
            if code in promocodes:
                promo = promocodes[code]
                if promo["used"] >= promo["uses"]:
                    await message.answer("❌ Промокод использован!")
                    return
                
                if promo["type"] == "brcoins":
                    user["brcoins"] += promo["amount"]
                    user["donate_received"] = user.get("donate_received", 0) + promo["amount"]
                else:
                    user["money"] += promo["amount"]
                    user["total_earned"] = user.get("total_earned", 0) + promo["amount"]
                
                promo["used"] += 1
                users[user_id] = user
                
                await save_promocodes(promocodes)
                await save_users(users)
                
                await message.answer(
                    f"✅ +{promo['amount']:,} "
                    f"{'BRcoins' if promo['type'] == 'brcoins' else '₽'}!"
                )
        except Exception as e:
            logger.error(f"Ошибка в handle_promo: {e}")
