import random
from datetime import datetime
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import bot, logger
from database.file_manager import load_users, save_users, load_inventory, save_inventory
from utils.helpers import check_access, get_default_user, is_function_disabled

# ==========================================
# ===== КОНФИГ РЫБАЛКИ =====
# ==========================================

# Удочки
FISHING_RODS = {
    "galactic": {
        "name": "Галактическая удочка",
        "emoji": "🚀",
        "base_chance": 95,
        "price": 20000000000,
        "criteria": {"fish_caught": 1500},
        "level": 5
    },
    "volcanic": {
        "name": "Вулканическая удочка",
        "emoji": "🌋",
        "base_chance": 85,
        "price": 1500000000,
        "criteria": {"fish_caught": 750},
        "level": 4
    },
    "legendary": {
        "name": "Легендарная удочка",
        "emoji": "⭐",
        "base_chance": 70,
        "price": 500000000,
        "criteria": {"fish_caught": 250},
        "level": 3
    },
    "rare": {
        "name": "Редкая удочка",
        "emoji": "🔮",
        "base_chance": 65,
        "price": 150000000,
        "criteria": {"fish_caught": 50},
        "level": 2
    },
    "basic": {
        "name": "Базовая удочка",
        "emoji": "🎣",
        "base_chance": 55,
        "price": 0,
        "criteria": {"default": True},
        "level": 1
    }
}

# Снасти (НЕ ТРАТЯТСЯ!)
FISHING_TACKLE = {
    "galactic": {
        "name": "Галактическая снасть",
        "emoji": "🚀",
        "price": 7500000000,
        "criteria": {"rod": "galactic"},
        "level": 5
    },
    "volcanic": {
        "name": "Вулканическая снасть",
        "emoji": "🌋",
        "price": 1500000000,
        "criteria": {"rod": "volcanic"},
        "level": 4
    },
    "legendary": {
        "name": "Легендарная снасть",
        "emoji": "⭐",
        "price": 350000000,
        "criteria": {"rod": "legendary"},
        "level": 3
    },
    "rare": {
        "name": "Редкая снасть",
        "emoji": "🔮",
        "price": 75000000,
        "criteria": {"rod": "rare"},
        "level": 2
    },
    "basic": {
        "name": "Базовая снасть",
        "emoji": "🎣",
        "price": 0,
        "criteria": {"default": True},
        "level": 1
    }
}

# Приманки (5 штук для каждой удочки)
FISHING_BAITS = {
    "galactic": [
        {"name": "Квантовая крошка", "price": 500000000, "bonus": 40},
        {"name": "Звёздная пыль", "price": 150000000, "bonus": 30},
        {"name": "Метеоритный песок", "price": 95000000, "bonus": 20},
        {"name": "Тёмная материя", "price": 85000000, "bonus": 15},
        {"name": "Солнечный луч", "price": 70000000, "bonus": 10}
    ],
    "volcanic": [
        {"name": "Лавовый червь", "price": 50000000, "bonus": 40},
        {"name": "Пепельный мотыль", "price": 35000000, "bonus": 25},
        {"name": "Магмовый опарыш", "price": 25000000, "bonus": 20},
        {"name": "Кратерная креветка", "price": 20000000, "bonus": 15},
        {"name": "Огненный нектар", "price": 15000000, "bonus": 10}
    ],
    "legendary": [
        {"name": "Золотая муха", "price": 25000000, "bonus": 40},
        {"name": "Жемчужная крупа", "price": 15000000, "bonus": 30},
        {"name": "Бриллиантовый червь", "price": 10000000, "bonus": 20},
        {"name": "Древний мотыль", "price": 8000000, "bonus": 15},
        {"name": "Королевский нектар", "price": 5000000, "bonus": 10}
    ],
    "rare": [
        {"name": "Серебряный опарыш", "price": 5000000, "bonus": 40},
        {"name": "Бронзовый червь", "price": 2500000, "bonus": 30},
        {"name": "Мраморная муха", "price": 2000000, "bonus": 20},
        {"name": "Янтарный мотыль", "price": 1500000, "bonus": 15},
        {"name": "Изумрудный нектар", "price": 1000000, "bonus": 10}
    ],
    "basic": [
        {"name": "Обычный червяк", "price": 15000, "bonus": 40},
        {"name": "Хлебный мякиш", "price": 7500, "bonus": 30},
        {"name": "Муха-дрозофила", "price": 5000, "bonus": 20},
        {"name": "Тесто", "price": 2500, "bonus": 15},
        {"name": "Универсальный нектар", "price": 1000, "bonus": 10}
    ]
}

# Рыбы по удочкам
FISH_DATA = {
    "galactic": [
        {"name": "Квантовый тунец", "price": 5000000, "chance": 65},
        {"name": "Звёздный скат", "price": 15000000, "chance": 60},
        {"name": "Чёрная дыра-рыба", "price": 50000000, "chance": 50},
        {"name": "Планетарная камбала", "price": 100000000, "chance": 45},
        {"name": "Комета-окунь", "price": 150000000, "chance": 35},
        {"name": "Астероидная сельдь", "price": 350000000, "chance": 25},
        {"name": "Гравитационный сом", "price": 750000000, "chance": 5},
        {"name": "Тёмный угорь", "price": 2500000000, "chance": 1},
        {"name": "Космический ёрш", "price": 5500000000, "chance": 0.2},
        {"name": "Пульсар-карась", "price": 7500000000, "chance": 0.05}
    ],
    "volcanic": [
        {"name": "Лавовый лосось", "price": 75000000, "chance": 60},
        {"name": "Огненный карп", "price": 150000000, "chance": 50},
        {"name": "Пепельная форель", "price": 250670670, "chance": 45},
        {"name": "Магмовый сом", "price": 350000000, "chance": 35},
        {"name": "Кратерный окунь", "price": 500000000, "chance": 25},
        {"name": "Вулканическая щука", "price": 750000000, "chance": 10},
        {"name": "Раскалённая плотва", "price": 1700670670, "chance": 1},
        {"name": "Серный судак", "price": 2500000000, "chance": 0.5},
        {"name": "Извергающий ёрш", "price": 3500000000, "chance": 0.3},
        {"name": "Жар-карась", "price": 5500000000, "chance": 0.09}
    ],
    "legendary": [
        {"name": "Королевский лосось", "price": 3500000, "chance": 60},
        {"name": "Серебряный судак", "price": 5000000, "chance": 45},
        {"name": "Бриллиантовая щука", "price": 7500000, "chance": 25},
        {"name": "Нефритовый окунь", "price": 15000000, "chance": 15},
        {"name": "Аметистовый сазан", "price": 750000000, "chance": 0.5},
        {"name": "Рубиновый ёрш", "price": 1500000000, "chance": 0.2}
    ],
    "rare": [
        {"name": "Жемчужный карась", "price": 1200000, "chance": 60},
        {"name": "Золотистый ёрш", "price": 7500000, "chance": 30},
        {"name": "Медный сом", "price": 15000000, "chance": 15},
        {"name": "Стальной окунь", "price": 250000000, "chance": 0.5},
        {"name": "Бирюзовый пескарь", "price": 500000000, "chance": 0.2}
    ],
    "basic": [
        {"name": "Карась", "price": 300000, "chance": 22},
        {"name": "Плотва", "price": 330000, "chance": 18},
        {"name": "Окунь", "price": 350000, "chance": 16},
        {"name": "Ёрш", "price": 450000, "chance": 13},
        {"name": "Пескарь", "price": 500000, "chance": 11},
        {"name": "Краснопёрка", "price": 1000000, "chance": 8},
        {"name": "Линь", "price": 2500000, "chance": 6},
        {"name": "Уклейка", "price": 3550000, "chance": 4},
        {"name": "Густера", "price": 7500000, "chance": 2},
        {"name": "Вьюн", "price": 150000000, "chance": 0.1}
    ]
}


def register_fishing_handlers(dp):
    
    async def get_fishing_data(user_id: str):
        """Получает данные рыбалки пользователя"""
        users = await load_users()
        user = users.get(user_id, get_default_user())
        return user.get("fishing", {
            "rod": "basic",
            "tackle": "basic",
            "bait": None,
            "fish_caught": 0,
            "total_fish": 0,
            "fish_inventory": {},
            "rods": {"basic": True},
            "tackles": {"basic": True}
        })
    
    async def save_fishing_data(user_id: str, fishing_data: dict):
        """Сохраняет данные рыбалки пользователя"""
        users = await load_users()
        user = users.get(user_id, get_default_user())
        user["fishing"] = fishing_data
        users[user_id] = user
        await save_users(users)
    
    async def get_fishing_inventory(user_id: str) -> list:
        """Получает инвентарь приманок из inventory.json"""
        inventory = await load_inventory()
        return inventory.get(user_id, [])
    
    async def add_to_inventory(user_id: str, item: str):
        """Добавляет предмет в инвентарь"""
        inventory = await load_inventory()
        if user_id not in inventory:
            inventory[user_id] = []
        inventory[user_id].append(item)
        await save_inventory(inventory)
    
    async def remove_from_inventory(user_id: str, item: str) -> bool:
        """Удаляет предмет из инвентаря"""
        inventory = await load_inventory()
        if user_id not in inventory:
            return False
        if item in inventory[user_id]:
            inventory[user_id].remove(item)
            await save_inventory(inventory)
            return True
        return False
    
    def get_fish(rod_key: str, bait_bonus: int = 0) -> dict:
        """Ловит рыбу с учётом приманки (бонус увеличивает шанс на редкую рыбу)"""
        fish_list = FISH_DATA.get(rod_key, FISH_DATA["basic"])
        
        # ✅ Приманка увеличивает шанс на редкую рыбу
        # Чем выше бонус, тем больше шанс выпасть редкой рыбе
        modified_fish_list = []
        for fish in fish_list:
            # Увеличиваем шанс для всех рыб, но особенно для редких
            if fish["chance"] < 10:  # Редкая рыба (шанс < 10%)
                modified_chance = fish["chance"] * (1 + bait_bonus / 100)
            elif fish["chance"] < 30:  # Средняя рыба (шанс 10-30%)
                modified_chance = fish["chance"] * (1 + bait_bonus / 200)
            else:  # Обычная рыба
                modified_chance = fish["chance"] * (1 + bait_bonus / 300)
            
            modified_fish_list.append({
                "name": fish["name"],
                "price": fish["price"],
                "chance": modified_chance
            })
        
        # Нормализуем шансы
        total_chance = sum(f["chance"] for f in modified_fish_list)
        if total_chance > 0:
            for fish in modified_fish_list:
                fish["chance"] = fish["chance"] / total_chance * 100
        
        # Выбираем рыбу
        roll = random.random() * 100
        cumulative = 0
        for fish in modified_fish_list:
            cumulative += fish["chance"]
            if roll <= cumulative:
                return fish
        
        return random.choice(modified_fish_list)
    
    # ==========================================
    # ===== ГЛАВНОЕ МЕНЮ РЫБАЛКИ =====
    # ==========================================
    
    @dp.callback_query(F.data == "work_fishing")
    async def fishing_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("job_5"):
            await callback.answer("⛔ Эта работа остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            
            rod_key = fishing.get("rod", "basic")
            rod = FISHING_RODS.get(rod_key, FISHING_RODS["basic"])
            tackle_key = fishing.get("tackle", "basic")
            tackle = FISHING_TACKLE.get(tackle_key, FISHING_TACKLE["basic"])
            bait_name = fishing.get("bait", "Не выбрана")
            
            text = (
                f"🎣 **РЫБАЛКА**\n\n"
                f"🎣 Удочка: {rod['emoji']} {rod['name']}\n"
                f"   🎯 Шанс: {rod['base_chance']}%\n"
                f"🔧 Снасть: {tackle['emoji']} {tackle['name']}\n"
                f"🐛 Приманка: {bait_name}\n"
                f"🐟 Поймано рыб: {fishing.get('fish_caught', 0)}\n"
                f"📦 Всего рыб: {fishing.get('total_fish', 0)}\n\n"
                f"Выберите действие:"
            )
            
            keyboard = [
                [InlineKeyboardButton(text="🎣 Рыбачить", callback_data="fishing_cast")],
                [InlineKeyboardButton(text="🏪 Магазин", callback_data="fishing_shop")],
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="fishing_settings")],
                [InlineKeyboardButton(text="📊 Статистика", callback_data="fishing_stats")],
                [InlineKeyboardButton(text="ℹ️ Информация", callback_data="fishing_info")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
            ]
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    # ==========================================
    # ===== РЫБАЧИТЬ =====
    # ==========================================
    
    @dp.callback_query(F.data == "fishing_cast")
    async def fishing_cast(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            
            rod_key = fishing.get("rod", "basic")
            rod = FISHING_RODS.get(rod_key, FISHING_RODS["basic"])
            bait_name = fishing.get("bait")
            
            # Проверяем приманку (если выбрана)
            bait_bonus = 0
            if bait_name:
                # Ищем приманку во всех категориях
                for category, baits in FISHING_BAITS.items():
                    for bait in baits:
                        if bait["name"] == bait_name:
                            bait_bonus = bait["bonus"]
                            break
                    if bait_bonus > 0:
                        break
                
                # Проверяем, есть ли приманка в инвентаре
                inventory = await get_fishing_inventory(user_id)
                bait_item = f"Приманка: {bait_name}"
                if bait_item not in inventory:
                    await callback.answer("❌ У вас нет выбранной приманки! Приманка используется 1 раз.", show_alert=True)
                    return
                
                # ✅ Тратим приманку
                await remove_from_inventory(user_id, bait_item)
            
            # ✅ Снасть НЕ ТРАТИТСЯ!
            
            # Ловим рыбу (бонус приманки увеличивает шанс на редкую рыбу)
            fish = get_fish(rod_key, bait_bonus)
            
            if fish:
                # Сохраняем рыбу в инвентарь
                inventory = await load_inventory()
                if user_id not in inventory:
                    inventory[user_id] = []
                inventory[user_id].append(fish["name"])
                await save_inventory(inventory)
                
                # Обновляем статистику
                fishing["fish_caught"] = fishing.get("fish_caught", 0) + 1
                fishing["total_fish"] = fishing.get("total_fish", 0) + 1
                
                if "fish_inventory" not in fishing:
                    fishing["fish_inventory"] = {}
                fishing["fish_inventory"][fish["name"]] = fishing["fish_inventory"].get(fish["name"], 0) + 1
                
                await save_fishing_data(user_id, fishing)
                
                bonus_text = f" (+{bait_bonus}% от приманки)" if bait_bonus > 0 else ""
                
                text = (
                    f"🎣 **УЛОВ!**\n\n"
                    f"🐟 {fish['name']}\n"
                    f"💰 Цена: {fish['price']:,.0f}₽\n"
                    f"📊 Шанс: {rod['base_chance']}%{bonus_text}\n"
                    f"🐛 Приманка использована"
                )
            else:
                await save_fishing_data(user_id, fishing)
                
                bonus_text = f" (+{bait_bonus}% от приманки)" if bait_bonus > 0 else ""
                
                text = (
                    f"🎣 **НИЧЕГО НЕ ПОЙМАЛИ!**\n\n"
                    f"😔 Рыба ушла...\n"
                    f"📊 Шанс: {rod['base_chance']}%{bonus_text}\n"
                    f"🐛 Приманка использована"
                )
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎣 Рыбачить ещё", callback_data="fishing_cast")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="work_fishing")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_cast: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    # ==========================================
    # ===== МАГАЗИН (С КНОПКАМИ!) =====
    # ==========================================
    
    @dp.callback_query(F.data == "fishing_shop")
    async def fishing_shop(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            keyboard = [
                [InlineKeyboardButton(text="🎣 Удочки", callback_data="fishing_rods")],
                [InlineKeyboardButton(text="🔧 Снасти", callback_data="fishing_tackle")],
                [InlineKeyboardButton(text="🐛 Приманки", callback_data="fishing_baits")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="work_fishing")]
            ]
            
            await callback.message.edit_text(
                "🏪 **МАГАЗИН РЫБАЛКИ**\n\nВыберите категорию:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_shop: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    # ==========================================
    # ===== УДОЧКИ (С КНОПКАМИ ПОКУПКИ) =====
    # ==========================================
    
    @dp.callback_query(F.data == "fishing_rods")
    async def fishing_rods(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            current_rod = fishing.get("rod", "basic")
            
            text = "🎣 **УДОЧКИ**\n\n"
            keyboard = []
            
            for key, rod in FISHING_RODS.items():
                is_owned = fishing.get("rods", {}).get(key, False) or key == "basic"
                is_current = key == current_rod
                
                status = "✅ ВЫБРАНА" if is_current else "✅ Есть" if is_owned else "❌ Нет"
                text += f"{rod['emoji']} {rod['name']} - {status}\n"
                text += f"   🎯 Шанс: {rod['base_chance']}%\n"
                
                if key != "basic":
                    criteria = rod.get("criteria", {})
                    if "fish_caught" in criteria:
                        text += f"   🐟 Нужно поймать: {criteria['fish_caught']} рыб\n"
                    text += f"   💰 Цена: {rod['price']:,.0f}₽\n"
                
                text += "\n"
                
                if is_owned and not is_current:
                    keyboard.append([InlineKeyboardButton(
                        text=f"📌 Выбрать {rod['emoji']} {rod['name']}",
                        callback_data=f"fishing_select_rod_{key}"
                    )])
                elif not is_owned and key != "basic":
                    if fishing.get("fish_caught", 0) >= rod.get("criteria", {}).get("fish_caught", 0):
                        keyboard.append([InlineKeyboardButton(
                            text=f"💰 Купить {rod['emoji']} {rod['name']} ({rod['price']:,.0f}₽)",
                            callback_data=f"fishing_buy_rod_{key}"
                        )])
            
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_shop")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_rods: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("fishing_select_rod_"))
    async def fishing_select_rod(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            rod_key = callback.data.replace("fishing_select_rod_", "")
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            
            fishing["rod"] = rod_key
            await save_fishing_data(user_id, fishing)
            
            rod = FISHING_RODS.get(rod_key, FISHING_RODS["basic"])
            await callback.answer(f"✅ Выбрана {rod['name']}!", show_alert=True)
            
            await fishing_rods(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_select_rod: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("fishing_buy_rod_"))
    async def fishing_buy_rod(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            rod_key = callback.data.replace("fishing_buy_rod_", "")
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            fishing = await get_fishing_data(user_id)
            
            rod = FISHING_RODS.get(rod_key)
            if not rod:
                await callback.answer("❌ Удочка не найдена!", show_alert=True)
                return
            
            if user["money"] < rod["price"]:
                await callback.answer(f"❌ Недостаточно средств! Нужно {rod['price']:,.0f}₽", show_alert=True)
                return
            
            user["money"] -= rod["price"]
            users[user_id] = user
            
            if "rods" not in fishing:
                fishing["rods"] = {}
            fishing["rods"][rod_key] = True
            
            await save_users(users)
            await save_fishing_data(user_id, fishing)
            
            await callback.answer(f"✅ Куплена {rod['name']}!", show_alert=True)
            await fishing_rods(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_buy_rod: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    # ==========================================
    # ===== СНАСТИ (С КНОПКАМИ ПОКУПКИ) =====
    # ==========================================
    
    @dp.callback_query(F.data == "fishing_tackle")
    async def fishing_tackle(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            current_tackle = fishing.get("tackle", "basic")
            current_rod = fishing.get("rod", "basic")
            
            text = "🔧 **СНАСТИ**\n\n"
            keyboard = []
            
            for key, tackle in FISHING_TACKLE.items():
                is_owned = fishing.get("tackles", {}).get(key, False) or key == "basic"
                is_current = key == current_tackle
                
                status = "✅ ВЫБРАНА" if is_current else "✅ Есть" if is_owned else "❌ Нет"
                text += f"{tackle['emoji']} {tackle['name']} - {status}\n"
                
                if key != "basic":
                    criteria = tackle.get("criteria", {})
                    if "rod" in criteria:
                        rod_needed = FISHING_RODS.get(criteria["rod"], {}).get("name", "Неизвестно")
                        text += f"   🎣 Нужна: {rod_needed}\n"
                    text += f"   💰 Цена: {tackle['price']:,.0f}₽\n"
                
                text += "\n"
                
                if is_owned and not is_current:
                    keyboard.append([InlineKeyboardButton(
                        text=f"📌 Выбрать {tackle['emoji']} {tackle['name']}",
                        callback_data=f"fishing_select_tackle_{key}"
                    )])
                elif not is_owned and key != "basic":
                    can_buy = False
                    if "rod" in tackle.get("criteria", {}):
                        required_rod = tackle["criteria"]["rod"]
                        if fishing.get("rods", {}).get(required_rod, False) or current_rod == required_rod:
                            can_buy = True
                    elif "default" in tackle.get("criteria", {}):
                        can_buy = True
                    
                    if can_buy:
                        keyboard.append([InlineKeyboardButton(
                            text=f"💰 Купить {tackle['emoji']} {tackle['name']} ({tackle['price']:,.0f}₽)",
                            callback_data=f"fishing_buy_tackle_{key}"
                        )])
            
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_shop")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_tackle: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("fishing_select_tackle_"))
    async def fishing_select_tackle(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            tackle_key = callback.data.replace("fishing_select_tackle_", "")
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            
            fishing["tackle"] = tackle_key
            await save_fishing_data(user_id, fishing)
            
            tackle = FISHING_TACKLE.get(tackle_key, FISHING_TACKLE["basic"])
            await callback.answer(f"✅ Выбрана {tackle['name']}!", show_alert=True)
            
            await fishing_tackle(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_select_tackle: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("fishing_buy_tackle_"))
    async def fishing_buy_tackle(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            tackle_key = callback.data.replace("fishing_buy_tackle_", "")
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            fishing = await get_fishing_data(user_id)
            
            tackle = FISHING_TACKLE.get(tackle_key)
            if not tackle:
                await callback.answer("❌ Снасть не найдена!", show_alert=True)
                return
            
            if user["money"] < tackle["price"]:
                await callback.answer(f"❌ Недостаточно средств! Нужно {tackle['price']:,.0f}₽", show_alert=True)
                return
            
            user["money"] -= tackle["price"]
            users[user_id] = user
            
            if "tackles" not in fishing:
                fishing["tackles"] = {}
            fishing["tackles"][tackle_key] = True
            
            await save_users(users)
            await save_fishing_data(user_id, fishing)
            
            await callback.answer(f"✅ Куплена {tackle['name']}!", show_alert=True)
            await fishing_tackle(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_buy_tackle: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    # ==========================================
    # ===== ПРИМАНКИ (С КНОПКАМИ ПОКУПКИ) =====
    # ==========================================
    
    @dp.callback_query(F.data == "fishing_baits")
    async def fishing_baits_menu(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            keyboard = [
                [InlineKeyboardButton(text="🚀 Галактические", callback_data="fishing_baits_galactic")],
                [InlineKeyboardButton(text="🌋 Вулканические", callback_data="fishing_baits_volcanic")],
                [InlineKeyboardButton(text="⭐ Легендарные", callback_data="fishing_baits_legendary")],
                [InlineKeyboardButton(text="🔮 Редкие", callback_data="fishing_baits_rare")],
                [InlineKeyboardButton(text="🎣 Базовые", callback_data="fishing_baits_basic")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_shop")]
            ]
            
            await callback.message.edit_text(
                "🐛 **ПРИМАНКИ**\n\nВыберите категорию:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_baits_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("fishing_baits_"))
    async def fishing_baits_category(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            category = callback.data.replace("fishing_baits_", "")
            baits = FISHING_BAITS.get(category, [])
            
            if not baits:
                await callback.answer("❌ Нет приманок в этой категории!", show_alert=True)
                return
            
            text = f"🐛 **{category.upper()} ПРИМАНКИ**\n\n"
            keyboard = []
            
            for bait in baits:
                text += f"• {bait['name']}\n"
                text += f"   💰 Цена: {bait['price']:,.0f}₽ (за шт.)\n"
                text += f"   📈 Бонус к шансу: +{bait['bonus']}%\n\n"
                
                keyboard.append([InlineKeyboardButton(
                    text=f"🛒 Купить {bait['name']}",
                    callback_data=f"fishing_buy_bait_{category}_{bait['name']}_{bait['price']}"
                )])
            
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="fishing_baits")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_baits_category: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("fishing_buy_bait_"))
    async def fishing_buy_bait(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            parts = callback.data.split("_")
            category = parts[3]
            # Название может содержать пробелы (восстанавливаем)
            bait_name = "_".join(parts[4:-1])
            price = int(parts[-1])
            
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if user["money"] < price:
                await callback.answer(f"❌ Недостаточно средств! Нужно {price:,.0f}₽", show_alert=True)
                return
            
            user["money"] -= price
            users[user_id] = user
            await save_users(users)
            
            # Добавляем приманку в инвентарь
            await add_to_inventory(user_id, f"Приманка: {bait_name}")
            
            await callback.answer(f"✅ Куплена приманка: {bait_name}!", show_alert=True)
            await fishing_baits_category(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_buy_bait: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    # ==========================================
    # ===== НАСТРОЙКИ =====
    # ==========================================
    
    @dp.callback_query(F.data == "fishing_settings")
    async def fishing_settings(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            
            rod_key = fishing.get("rod", "basic")
            rod = FISHING_RODS.get(rod_key, FISHING_RODS["basic"])
            tackle_key = fishing.get("tackle", "basic")
            tackle = FISHING_TACKLE.get(tackle_key, FISHING_TACKLE["basic"])
            current_bait = fishing.get("bait", "Не выбрана")
            
            # Получаем все приманки из инвентаря
            inventory = await get_fishing_inventory(user_id)
            baits_inventory = []
            for item in inventory:
                if item.startswith("Приманка: "):
                    bait_name = item.replace("Приманка: ", "")
                    baits_inventory.append(bait_name)
            
            text = (
                f"⚙️ **НАСТРОЙКИ РЫБАЛКИ**\n\n"
                f"🎣 Удочка: {rod['emoji']} {rod['name']}\n"
                f"🔧 Снасть: {tackle['emoji']} {tackle['name']}\n"
                f"🐛 Текущая приманка: {current_bait}\n"
                f"📦 Приманок в инвентаре: {len(baits_inventory)}\n\n"
                f"Выберите приманку для использования:"
            )
            
            keyboard = []
            
            if baits_inventory:
                for bait_name in baits_inventory[:10]:
                    is_selected = bait_name == current_bait
                    keyboard.append([InlineKeyboardButton(
                        text=f"{'✅' if is_selected else '🐛'} {bait_name}",
                        callback_data=f"fishing_select_bait_{bait_name}"
                    )])
            else:
                keyboard.append([InlineKeyboardButton(
                    text="❌ Нет приманок",
                    callback_data="fishing_no_baits"
                )])
            
            keyboard.append([InlineKeyboardButton(
                text="❌ Снять приманку",
                callback_data="fishing_remove_bait"
            )])
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="work_fishing")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_settings: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    @dp.callback_query(F.data.startswith("fishing_select_bait_"))
    async def fishing_select_bait(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            bait_name = callback.data.replace("fishing_select_bait_", "")
            user_id = str(callback.from_user.id)
            
            # Проверяем, есть ли приманка в инвентаре
            inventory = await get_fishing_inventory(user_id)
            bait_item = f"Приманка: {bait_name}"
            if bait_item not in inventory:
                await callback.answer("❌ У вас нет этой приманки!", show_alert=True)
                return
            
            fishing = await get_fishing_data(user_id)
            fishing["bait"] = bait_name
            await save_fishing_data(user_id, fishing)
            
            await callback.answer(f"✅ Выбрана приманка: {bait_name}!", show_alert=True)
            await fishing_settings(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_select_bait: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    @dp.callback_query(F.data == "fishing_remove_bait")
    async def fishing_remove_bait(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            fishing["bait"] = None
            await save_fishing_data(user_id, fishing)
            
            await callback.answer("✅ Приманка снята!", show_alert=True)
            await fishing_settings(callback)
        except Exception as e:
            logger.error(f"Ошибка в fishing_remove_bait: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    @dp.callback_query(F.data == "fishing_no_baits")
    async def fishing_no_baits(callback: types.CallbackQuery):
        await callback.answer("Купите приманки в магазине!", show_alert=True)
    
    # ==========================================
    # ===== СТАТИСТИКА =====
    # ==========================================
    
    @dp.callback_query(F.data == "fishing_stats")
    async def fishing_stats(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            fishing = await get_fishing_data(user_id)
            
            rod_key = fishing.get("rod", "basic")
            rod = FISHING_RODS.get(rod_key, FISHING_RODS["basic"])
            
            tackle_key = fishing.get("tackle", "basic")
            tackle = FISHING_TACKLE.get(tackle_key, FISHING_TACKLE["basic"])
            
            fish_inventory = fishing.get("fish_inventory", {})
            total_fish = sum(fish_inventory.values())
            
            text = (
                f"📊 **СТАТИСТИКА РЫБАЛКИ**\n\n"
                f"🎣 Удочка: {rod['emoji']} {rod['name']}\n"
                f"🔧 Снасть: {tackle['emoji']} {tackle['name']}\n"
                f"🐟 Всего поймано: {fishing.get('total_fish', 0)}\n"
                f"📦 Разных рыб: {len(fish_inventory)}\n\n"
                f"**Топ-3 рыбы:**\n"
            )
            
            sorted_fish = sorted(fish_inventory.items(), key=lambda x: x[1], reverse=True)[:3]
            for name, count in sorted_fish:
                text += f"• {name}: {count} шт.\n"
            
            if not sorted_fish:
                text += "• Нет рыб\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="work_fishing")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_stats: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
    
    # ==========================================
    # ===== ИНФОРМАЦИЯ =====
    # ==========================================
    
    @dp.callback_query(F.data == "fishing_info")
    async def fishing_info(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            text = (
                "ℹ️ **ИНФОРМАЦИЯ О РЫБАЛКЕ**\n\n"
                "**🎣 УДОЧКИ:**\n"
                "1. 🚀 Галактическая (95%) - 1500 рыб, 20,000,000,000₽\n"
                "2. 🌋 Вулканическая (85%) - 750 рыб, 1,500,000,000₽\n"
                "3. ⭐ Легендарная (70%) - 250 рыб, 500,000,000₽\n"
                "4. 🔮 Редкая (65%) - 50 рыб, 150,000,000₽\n"
                "5. 🎣 Базовая (55%) - бесплатно\n\n"
                "**🔧 СНАСТИ (НЕ ТРАТЯТСЯ!):**\n"
                "1. 🚀 Галактическая - 7,500,000,000₽\n"
                "2. 🌋 Вулканическая - 1,500,000,000₽\n"
                "3. ⭐ Легендарная - 350,000,000₽\n"
                "4. 🔮 Редкая - 75,000,000₽\n"
                "5. 🎣 Базовая - бесплатно\n\n"
                "**🐛 ПРИМАНКИ (ТРАТЯТСЯ 1 РАЗ):**\n"
                "Увеличивают шанс на поимку РЕДКОЙ рыбы.\n"
                "Чем выше бонус → тем больше шанс редкой рыбы.\n"
                "Доступны в магазине по 5 штук на удочку.\n"
                "Для использования выберите в настройках.\n\n"
                "**🐟 РЫБЫ:**\n"
                "Разные рыбы для каждой удочки.\n"
                "Чем реже рыба → тем выше цена.\n"
                "Продавать рыбу можно у Скупщика."
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="work_fishing")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в fishing_info: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
