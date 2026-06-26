from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import bot, logger, ADMIN_IDS
from database.file_manager import (
    load_users, save_users, load_inventory, save_inventory,
    load_promocodes, save_promocodes, load_settings
)
from utils.helpers import (
    check_access, get_default_user, check_subscription,
    is_function_disabled, is_admin, generate_referral_link,
    get_referral_reward, generate_captcha
)
from services.currency import currency_rates

# ✅ Импорты из casino
try:
    from handlers.casino import mines_games, mines_games_by_id, get_min_mines_for_size
except ImportError:
    mines_games = {}
    mines_games_by_id = {}
    def get_min_mines_for_size(size: int) -> int:
        min_mines = {3: 2, 4: 3, 5: 5, 6: 7, 7: 9, 8: 13}
        return min_mines.get(size, 2)

from handlers.auction import show_auction_lot

# States
from states import (
    SupportStates, AuctionStates, TradeStates, CasinoStates
)

def register_user_handlers(dp):
    
    async def get_main_menu(user_id: str):
        """Главное меню"""
        users = await load_users()
        user = users.get(user_id, get_default_user())
        
        currency_rates.update_rates()
        
        text = (
            f"👋 **Главное меню**\n\n"
            f"💰 Баланс: {user['money']:,.0f}₽\n"
            f"🔒 Заморожено: {user.get('frozen_balance', 0):,.0f}₽\n"
            f"💎 BRcoins: {user['brcoins']}\n"
            f"₿ BTC: {user['portfolio'].get('BTC', 0)}\n"
            f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}\n"
            f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}"
        )
        
        keyboard = [
            [
                InlineKeyboardButton(text="👨 Профиль", callback_data="profile_menu"),
                InlineKeyboardButton(text="💼 Работы", callback_data="works"),
                InlineKeyboardButton(text="💎 Донат", callback_data="donate")
            ],
            [
                InlineKeyboardButton(text="🚀 Развлечения", callback_data="entertainment_menu"),
                InlineKeyboardButton(text="🧙‍♀️ Скупщик", callback_data="buyer"),
                InlineKeyboardButton(text="🏢 Бизнес", callback_data="business")
            ]
        ]
        
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # ==========================================
    # ===== START С КАПЧЕЙ =====
    # ==========================================
    
    @dp.message(Command("start"))
    async def start_command(message: types.Message, state: FSMContext):  # ← ДОБАВИЛИ state
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
            
            # ✅ Проверяем реферальную ссылку
            referrer_id = None
            if " " in message.text:
                parts = message.text.split()
                if len(parts) > 1 and parts[1].startswith("ref_"):
                    referrer_id = parts[1].replace("ref_", "")
            
            # ✅ Если пользователь НОВЫЙ
            if user_id not in users:
                # ✅ Показываем капчу
                correct_emoji, emojis = generate_captcha()
                
                await message.answer(
                    f"🛡️ **Добро пожаловать в WeteroRussia!** 😉\n\n"
                    f"Чтобы пользоваться ботом, пройдите капчу.\n"
                    f"Выберите верный эмодзи: **{correct_emoji}**",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=e, callback_data=f"captcha_{i}_{correct_emoji}") 
                         for i, e in enumerate(emojis[:3])],
                        [InlineKeyboardButton(text=e, callback_data=f"captcha_{i}_{correct_emoji}") 
                         for i, e in enumerate(emojis[3:6])]
                    ]),
                    parse_mode="Markdown"
                )
                
                await state.update_data(
                    captcha_correct=correct_emoji,
                    captcha_referrer=referrer_id
                )
                return
            
            # ✅ Если пользователь уже есть в базе
            if not await check_access(message):
                return
            
            # Проверяем незавершенную игру в казино
            if user_id in mines_games:
                game = mines_games[user_id]
                total_cells = game["field_size"] * game["field_size"]
                safe_cells = total_cells - game["mines_count"]
                
                if len(game["revealed"]) == safe_cells:
                    del mines_games[user_id]
                else:
                    await message.answer(
                        "⚠️ У вас есть незавершённая игра в казино!\n"
                        "Завершите игру прежде чем перейти в главное меню.",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="💣 Продолжить игру", callback_data="mines_play")],
                            [InlineKeyboardButton(text="❌ Завершить игру", callback_data="mines_cancel")]
                        ])
                    )
                    return
            
            text, keyboard = await get_main_menu(user_id)
            await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")
    
    # ==========================================
    # ===== ОБРАБОТЧИК КАПЧИ =====
    # ==========================================
    
    @dp.callback_query(F.data.startswith("captcha_"))
    async def captcha_handler(callback: types.CallbackQuery, state: FSMContext):
        user_id = str(callback.from_user.id)
        
        try:
            parts = callback.data.split("_")
            index = int(parts[1])
            correct_emoji = parts[2]
            
            # Получаем данные из state
            data = await state.get_data()
            stored_correct = data.get("captcha_correct")
            referrer_id = data.get("captcha_referrer")
            
            # Проверяем правильность
            if callback.data.endswith(correct_emoji):
                # ✅ Капча пройдена
                users = await load_users()
                
                # Создаём пользователя
                new_user = get_default_user()
                new_user["captcha_passed"] = True
                
                if referrer_id and referrer_id in users:
                    # ✅ Применяем рефералку
                    new_user["referrer"] = referrer_id
                    users[referrer_id]["referrals"].append(user_id)
                    users[referrer_id]["referral_count"] += 1
                    
                    # Выдаём награду рефереру
                    referrer, reward_text = get_referral_reward(referrer_id, users)
                    users[referrer_id] = referrer
                    
                    await save_users(users)
                    
                    try:
                        await bot.send_message(
                            int(referrer_id),
                            f"🎉 **Новый реферал!**\n\n"
                            f"👤 @{callback.from_user.username or 'Игрок'} присоединился по вашей ссылке!\n"
                            f"🎁 Награда: {reward_text}",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось уведомить реферера: {e}")
                
                # Сохраняем нового пользователя
                users[user_id] = new_user
                await save_users(users)
                await state.clear()
                
                await callback.message.edit_text(
                    "✅ **Капча пройдена!** Добро пожаловать в WeteroRussia! 🎉\n\n"
                    "Теперь у вас есть доступ ко всем функциям бота.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🚀 В главное меню", callback_data="back_main")]
                    ]),
                    parse_mode="Markdown"
                )
            else:
                # ❌ Капча не пройдена
                await callback.answer("❌ Неверный эмодзи! Попробуйте ещё раз.", show_alert=True)
                
                # Генерируем новую капчу
                correct_emoji, emojis = generate_captcha()
                await state.update_data(captcha_correct=correct_emoji)
                
                await callback.message.edit_text(
                    f"🛡️ **Попробуйте ещё раз!**\n\n"
                    f"Выберите верный эмодзи: **{correct_emoji}**",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=e, callback_data=f"captcha_{i}_{correct_emoji}") 
                         for i, e in enumerate(emojis[:3])],
                        [InlineKeyboardButton(text=e, callback_data=f"captcha_{i}_{correct_emoji}") 
                         for i, e in enumerate(emojis[3:6])]
                    ]),
                    parse_mode="Markdown"
                )
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Ошибка в captcha_handler: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
    
    # ==========================================
    # ===== НАЗАД =====
    # ==========================================
    
    @dp.callback_query(F.data == "back_main")
    async def back_main(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return
        
        try:
            text, keyboard = await get_main_menu(str(callback.from_user.id))
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка в back_main: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    # ==========================================
    # ===== ПРОФИЛЬ =====
    # ==========================================
    
    @dp.callback_query(F.data == "profile_menu")
    async def profile_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return
        
        try:
            keyboard = [
                [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
                [InlineKeyboardButton(text="🏠 Гараж", callback_data="garage")],
                [InlineKeyboardButton(text="📦 Инвентарь", callback_data="inventory_main")],
                [InlineKeyboardButton(text="🏆 Форбс", callback_data="forbes")],
                [InlineKeyboardButton(text="👥 Реф.Система", callback_data="referral_system")],
                [InlineKeyboardButton(text="🆘 Тех.поддержка", callback_data="support")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            
            await callback.message.edit_text(
                "👨 **Профиль**\n\nВыберите раздел:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в profile_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    # ==========================================
    # ===== РЕФЕРАЛЬНАЯ СИСТЕМА =====
    # ==========================================
    
    @dp.callback_query(F.data == "referral_system")
    async def referral_system(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            referrals = user.get("referrals", [])
            referral_count = user.get("referral_count", 0)
            
            # Собираем никнеймы приглашённых
            referral_names = []
            for ref_id in referrals[:10]:
                try:
                    ref_user = await bot.get_chat(int(ref_id))
                    name = f"@{ref_user.username}" if ref_user.username else f"ID: {ref_id[:5]}"
                    referral_names.append(name)
                except:
                    referral_names.append(f"ID: {ref_id[:5]}")
            
            referral_list = "\n".join([f"• {name}" for name in referral_names]) if referral_names else "Нет приглашённых"
            
            # ✅ Генерируем ссылку через await
            link = await generate_referral_link(user_id)
            
            text = (
                f"👥 **Реферальная система**\n\n"
                f"📊 Приглашено: {referral_count} чел.\n"
                f"💰 Награда за 1 реферала: 150,000,000₽ + 🚗 (шанс 20%)\n\n"
                f"📋 **Ваши рефералы:**\n{referral_list}\n\n"
                f"🔗 **Ваша ссылка:**\n`{link}`\n\n"
                f"Отправьте эту ссылку друзьям и получайте награды!"
            )
            
            keyboard = [
                [InlineKeyboardButton(text="📤 Поделиться ссылкой", callback_data="share_referral")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
            ]
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в referral_system: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    @dp.callback_query(F.data == "share_referral")
    async def share_referral(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            link = await generate_referral_link(user_id)  # ← await!
            
            await callback.message.answer(
                f"🔗 **Ваша реферальная ссылка:**\n\n"
                f"`{link}`\n\n"
                f"📤 Отправьте её друзьям! За каждого приглашённого вы получите 150,000,000₽ и шанс на машину!",
                parse_mode="Markdown"
            )
            await callback.answer()
        except Exception as e:
            logger.error(f"Ошибка в share_referral: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    # ==========================================
    # ===== СТАТИСТИКА =====
    # ==========================================
    
    @dp.callback_query(F.data == "stats")
    async def stats_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
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
                f"📊 **СТАТИСТИКА**\n\n"
                f"💰 Баланс: {user['money']:,.0f}₽\n"
                f"🔒 Заморожено: {user.get('frozen_balance', 0):,.0f}₽\n"
                f"💎 BRcoins: {user['brcoins']}\n"
                f"📈 Заработано: {user['total_earned']:,.0f}₽\n"
                f"🤝 Сделок: {user['trades_count']}\n"
                f"👤 Роль: {'Админ' if user['role'] == 'admin' else 'Игрок'}\n"
                f"🚗 Машин: {len(user.get('inventory', []))}\n"
                f"📦 Ресурсов: {resources_count}\n"
                f"⛏️ Попыток: {user['mine_attempts']}/100\n"
                f"🏢 Бизнесов: {business_count}\n"
                f"🤖 Авто-сбор: {auto_collect_count} бизнесов\n"
                f"👥 Рефералов: {user.get('referral_count', 0)}\n\n"
                f"📈 **Портфель:**\n"
                f"₿ BTC: {user['portfolio'].get('BTC', 0)}/150\n"
                f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}/100\n"
                f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}/5000"
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в stats_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    # ==========================================
    # ===== ПОДДЕРЖКА =====
    # ==========================================
    
    @dp.callback_query(F.data == "support")
    async def support_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_10"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            await callback.message.edit_text(
                "🆘 **ТЕХНИЧЕСКАЯ ПОДДЕРЖКА**\n\n"
                "Напишите ваше сообщение для администратора.\n"
                "Мы ответим вам в ближайшее время.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
                ]),
                parse_mode="Markdown"
            )
            await state.set_state(SupportStates.waiting_for_support_message)
            await callback.answer()
        except Exception as e:
            logger.error(f"Ошибка в support_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ГАРАЖ =====
    # ==========================================
    
    @dp.callback_query(F.data == "garage")
    async def garage_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
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
                    "🏠 **Ваш гараж пуст!**\n\n"
                    "💡 Получайте машины через админов или в будущих акциях!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
                    ]),
                    parse_mode="Markdown"
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
            
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")])
            
            await callback.message.edit_text(
                f"🏠 **Ваш гараж** ({len(user['inventory'])} машин):",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
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
                f"🚗 **{car['name']}**\n\n"
                f"💰 Стоимость: {car['price']:,.0f}₽\n"
                f"💵 Продажа: {int(car['price'] * 0.6):,.0f}₽ (60%)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
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
                f"💰 **Продано!**\n\n"
                f"🚗 {car['name']}\n"
                f"💳 Получено: {sell_price:,.0f}₽ (60% от цены)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В гараж", callback_data="garage")]
                ]),
                parse_mode="Markdown"
            )
        except (ValueError, IndexError):
            await callback.answer("❌ Ошибка в данных!")
        except Exception as e:
            logger.error(f"Ошибка в car_sell: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ИНВЕНТАРЬ =====
    # ==========================================
    
    @dp.callback_query(F.data == "inventory_main")
    async def inventory_main_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
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
                    "📦 **Ваш инвентарь пуст!**\n\n"
                    "Добывайте ресурсы в шахте или на ферме.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
                    ]),
                    parse_mode="Markdown"
                )
                await callback.answer()
                return
            
            from config import MINE_RESOURCES, FARM_RESOURCES
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            resources = {}
            for item in inventory[user_id]:
                resources[item] = resources.get(item, 0) + 1
            
            text = "📦 **ВАШ ИНВЕНТАРЬ:**\n\n"
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
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в inventory_main_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ФОРБС =====
    # ==========================================
    
    @dp.callback_query(F.data == "forbes")
    async def forbes_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
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
                [InlineKeyboardButton(text="👥 Топ рефералов", callback_data="forbes_referrals")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
            ]
            
            await callback.message.edit_text(
                "🏆 **Форбс**\n\nВыберите категорию:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
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
            
            text = "🏆 **Топ-10 по деньгам:**\n\n"
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
                ]),
                parse_mode="Markdown"
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
            
            text = "💎 **Топ-10 по BRcoins:**\n\n"
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
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в forbes_br: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "forbes_referrals")
    async def forbes_referrals(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            users = await load_users()
            sorted_users = sorted(
                users.items(),
                key=lambda x: x[1].get("referral_count", 0),
                reverse=True
            )[:10]
            
            if not sorted_users:
                await callback.answer("Нет данных")
                return
            
            text = "👥 **Топ-10 рефералов:**\n\n"
            for i, (user_id, data) in enumerate(sorted_users, 1):
                try:
                    user = await bot.get_chat(int(user_id))
                    username = user.username or f"User_{user_id[:5]}"
                except:
                    username = f"User_{user_id[:5]}"
                text += f"{i}. @{username} — {data.get('referral_count', 0)} чел.\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="forbes")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в forbes_referrals: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ДОНАТ =====
    # ==========================================
    
    @dp.callback_query(F.data == "donate")
    async def donate_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
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
                "💎 **Донат**\n\nКурс: 1₽ = 10 BRcoins\n@weterochina",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
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
                "💳 **Обратитесь к @weterochina**",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
                ]),
                parse_mode="Markdown"
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
                "🎫 **Введите промокод в чат**",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
                ]),
                parse_mode="Markdown"
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
                f"💰 **Баланс доната**\n\n"
                f"Потрачено: {user['donate_spent']}₽\n"
                f"Получено: {user['donate_received']} BRcoins\n"
                f"Баланс: {user['brcoins']} BRcoins",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в donate_balance: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== СКУПЩИК =====
    # ==========================================
    
    @dp.callback_query(F.data == "buyer")
    async def buyer_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
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
                    "📦 **Ваш инвентарь пуст!**\n\n"
                    "Добывайте ресурсы в шахте или на ферме.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                    ]),
                    parse_mode="Markdown"
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
                "🧙‍♀️ **СКУПЩИК**\n\nВыберите ресурс для продажи:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в buyer_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ОСТАЛЬНЫЕ ОБРАБОТЧИКИ =====
    # ==========================================
    
    # ... (остальные обработчики buyer_resource_menu, buyer_sell_one, buyer_sell_all_resource, buyer_sell_all, continue_mines_game, handle_all_messages остаются без изменений)
