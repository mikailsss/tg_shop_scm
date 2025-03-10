from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import TG_CHANNEL_LINK, SUPPORT_LINK

async def start_kb(tg_id):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛍️ Товары', callback_data='items')],
        [InlineKeyboardButton(text='💬 Поддержка', url=SUPPORT_LINK)],
        [InlineKeyboardButton(text='📰 Новости', url=TG_CHANNEL_LINK)],
        [InlineKeyboardButton(text='👤 Профиль', callback_data=f'my_profile_{tg_id}')]
    ])
    return kb

async def admin_start_kb(tg_id):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛍️ Товары', callback_data='items')],
        [InlineKeyboardButton(text='📥 Пополнить базу', callback_data='top_up')],
        [InlineKeyboardButton(text='📂 Расширенный каталог', callback_data='big_catalog')],
        [InlineKeyboardButton(text='🗑️ Удалить категорию', callback_data='delete_category')],
    ])  
    return kb

async def add_category_keyboard(categories):
    keyboard = InlineKeyboardBuilder()
    for category in categories:
        keyboard.add(InlineKeyboardButton(
            text=f"📂 {category.name}",
            callback_data=f'add_{category.id}'
        ))
    keyboard.add(InlineKeyboardButton(
        text='🔙 Назад',
        callback_data='get_menu'
    ))
    return keyboard.adjust(1).as_markup()

async def buy_category_keyboard(categories):
    keyboard = InlineKeyboardBuilder()
    for category in categories:
        keyboard.add(InlineKeyboardButton(
            text=f"📦 {category.name}",
            callback_data=f'choose_{category.id}'
        ))
    keyboard.add(InlineKeyboardButton(
        text='🔙 Назад',
        callback_data='get_menu'
    ))
    return keyboard.adjust(1).as_markup()

async def buy_buy_item(category_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{category_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="items")]
    ])
    return keyboard

async def create_user_profile(tg_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📜 История покупок', callback_data=f'history_{tg_id}')],
        [InlineKeyboardButton(text='💳 Пополнить баланс', callback_data=f'top_up_{tg_id}')],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='get_menu')]
    ])
    return keyboard

async def choose_payment(tg_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💎 CRYPTO_BOT', callback_data=f'crypto_{tg_id}' )],
        [InlineKeyboardButton(text='💰 LOLZ', callback_data=f'lolz_{tg_id}' )]
    ])
    return keyboard

async def top_up_cancel_kb(tg_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='❌ Отмена', callback_data=f'my_profile_{tg_id}')]
    ])
    return keyboard

async def lolz_top_up_kb(tg_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Проверить', callback_data=f'check_payment_{tg_id}')],
        [InlineKeyboardButton(text='❌ Отмена', callback_data=f'my_profile_{tg_id}')]
    ])
    return keyboard