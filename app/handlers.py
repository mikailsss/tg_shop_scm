import logging
import os
from aiogram import Router, Bot, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_LIST, BOT_TOKEN, CRYPTO_BOT_TOKEN, LOLZ_TOKEN, LOLZ_LINK
from database.requests import (
    new_user, get_categories, get_category, get_available_items,
    create_purchases, delete_items, update_user_balance, get_user_balance,
    add_items_from_file, get_user_balance_and_top_up, get_purchase_history
)
from .keyboards import (
    start_kb, admin_start_kb, buy_category_keyboard, add_category_keyboard,
    buy_buy_item, create_user_profile, top_up_cancel_kb,
    choose_payment, lolz_top_up_kb
)
from aiocryptopay import AioCryptoPay

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CRYPTO_PAY = AioCryptoPay(CRYPTO_BOT_TOKEN)
router = Router()
bot = Bot(BOT_TOKEN)

# Состояния для FSM
class ItemStates(StatesGroup):
    category = State()
    file = State()
    quantity = State()

class CryptoPayment(StatesGroup):
    amount = State()
    tg_id = State()

class LolzPayment(StatesGroup):
    amount = State()
    tg_id = State()
    order_id = State()

# Обработчик команды /start
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await new_user(message.from_user.id)
    kb = await admin_start_kb(message.from_user.id) if message.from_user.id in ADMIN_LIST else await start_kb(message.from_user.id)
    await message.answer(
        f'👋 Привет, {message.from_user.first_name}, добро пожаловать в магазин! 🛍️\n'
        'Выбери действие в меню ниже:',
        reply_markup=kb
    )

# Обработчик для возврата в меню
@router.callback_query(F.data == 'get_menu')
async def cmd_start_keck(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    kb = await admin_start_kb(callback.from_user.id) if callback.from_user.id in ADMIN_LIST else await start_kb(callback.from_user.id)
    await callback.message.edit_text(
        f'👋 Привет, {callback.from_user.first_name}, добро пожаловать в магазин! 🛍️\n'
        'Выбери действие в меню ниже:',
        reply_markup=kb
    )

# Обработчик для выбора категории товаров
@router.callback_query(F.data == 'items')
async def cmd_get_category(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        '📂 Выбери категорию товаров:',
        reply_markup=await buy_category_keyboard(await get_categories())
    )

# Обработчик для выбора товара в категории
@router.callback_query(F.data.startswith('choose_'))
async def cmd_buy_item(callback: CallbackQuery):
    try:
        await callback.answer()
        category_id = int(callback.data.split('_')[1])
        category_data = await get_category(category_id)
        
        if not category_data:
            await callback.message.answer("❌ Товар не найден.\nМеню - /start")
            return
        
        items_count = len(await get_available_items(category_id, 1000))
        await callback.message.edit_text(
            f'🎉 Категория: {category_data.name}\n'
            f'📝 Описание: {category_data.desc}\n'
            f'📦 Наличие: {items_count} шт.\n'
            f'💵 Цена: {category_data.price} руб. за одну почту',
            reply_markup=await buy_buy_item(category_id)
        )
    except Exception as e:
        logger.error(f"Ошибка в cmd_buy_item: {e}")
        await callback.message.answer("⚠️ Ошибка. Попробуй позже.\nМеню - /start")

# Обработчик для начала покупки
@router.callback_query(F.data.startswith('buy_'))
async def handle_buy_start(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        category_id = int(callback.data.split('_')[1])
        await state.update_data(category_id=category_id)
        await state.set_state(ItemStates.quantity)
        await callback.message.answer("🔢 Введи количество почт для покупки:")
    except Exception as e:
        logger.error(f"Ошибка в handle_buy_start: {e}")
        await callback.message.answer("⚠️ Ошибка. Попробуй позже.\nМеню - /start")

# Обработчик для ввода количества товаров
@router.message(ItemStates.quantity)
async def handle_buy_quantity(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        category_id = data.get('category_id')
        category = await get_category(category_id)
        user_tg_id = message.from_user.id
        
        if not message.text.isdigit():
            await message.answer("❌ Введи число!\nМеню - /start")
            return
        
        quantity = int(message.text)
        if quantity <= 0:
            await message.answer("❌ Количество должно быть больше нуля!\nМеню - /start")
            return
        
        available_items = await get_available_items(category_id, quantity)
        if len(available_items) < quantity:
            await message.answer(f"❌ Доступно только {len(available_items)} шт.")
            return
        
        total_price = category.price * quantity
        user_balance = await get_user_balance(user_tg_id)
        if user_balance < total_price:
            await message.answer(f"❌ Недостаточно средств. Нужно: {total_price} руб.\nТвой баланс: {user_balance} руб.\nМеню - /start")
            return
        
        await update_user_balance(user_tg_id, -total_price)
        await create_purchases(user_tg_id, category_id, available_items)
        await delete_items(available_items)
        
        items_info = "\n".join(f"{item.login}" for item in available_items)
        await message.answer(
            f"✅ Успешно куплено {quantity} шт.\n"
            f"💸 Списано: {total_price} руб.\n"
            f"📂 Категория: {category.name}\n"
            f"📦 Данные:\n\n{items_info}\n\n"
            'Меню - /start'
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка в handle_buy_quantity: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуй позже.\nМеню - /start")

# Обработчик для пополнения баланса через Lolz
@router.callback_query(F.data.startswith('lolz_'))
async def create_lolz_payment(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await state.clear()
        tg_id = int(callback.data.split('_')[1])
        await state.update_data(tg_id=tg_id)
        await callback.message.edit_text(
            '💳 Введите желаемую сумму пополнения в рублях:',
            reply_markup=await top_up_cancel_kb(tg_id)
        )
        await state.set_state(LolzPayment.amount)
    except Exception as e:
        logger.error(f"Ошибка в create_lolz_payment: {e}")
        await callback.message.answer("⚠️ Произошла ошибка. Попробуйте позже.\nМеню - /start")

# Обработчик для завершения пополнения через Lolz
@router.message(LolzPayment.amount)
async def top_up_end(message: Message, state: FSMContext):
    try:
        if not message.text.isdigit():
            await message.answer("❌ Введите число!\nМеню - /start")
            return
        
        amount = int(message.text)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше нуля!\nМеню - /start")
            return
        
        order_id = os.urandom(15).hex()
        await state.update_data(order_id=order_id, amount=amount)
        
        pay_url = LOLZ_TOKEN.get_payment_link(amount=amount, comment=order_id)
        await message.answer(
            f'💳 Оплатите {amount} руб. по ссылке: {pay_url}\n\n'
            'После оплаты нажмите кнопку "Проверить оплату".',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_lolz_payment_{order_id}")]
            ])
        )
    except Exception as e:
        logger.error(f"Ошибка в top_up_end: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.\nМеню - /start")

# Обработчик для проверки оплаты через Lolz
@router.callback_query(F.data.startswith('check_lolz_payment_'))
async def check_lolz_payment(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        order_id = callback.data.split('_')[2]
        data = await state.get_data()
        amount = data.get('amount')
        tg_id = data.get('tg_id')
        
        if not amount or not tg_id:
            await callback.message.answer("❌ Не удалось найти данные о платеже.\nМеню - /start")
            return
        
        payment_info = await LOLZ_TOKEN.check_status_payment(amount, comment=order_id)
        if payment_info:
            await update_user_balance(tg_id, amount)
            await callback.message.answer(
                f"✅ Платеж подтвержден! Сумма: {amount} руб.\n"
                f"Ваш баланс успешно пополнен. 🎉\nМеню - /start"
            )
            await state.clear()
        else:
            await callback.message.answer("❌ Платеж не найден. Попробуйте позже.\nМеню - /start")
    except Exception as e:
        logger.error(f"Ошибка в check_lolz_payment: {e}")
        await callback.message.answer("⚠️ Произошла ошибка. Попробуйте позже.\nМеню - /start")