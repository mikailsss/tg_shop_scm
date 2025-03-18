import logging
import os
from database.models import async_session
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Router, Bot, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_LIST, BOT_TOKEN, CRYPTO_BOT_TOKEN, LOLZ_TOKEN, USD_RUB_COURSE
from database.requests import (
    new_user, get_categories, get_category, get_available_items,
    create_purchases, delete_items, update_user_balance, get_user_balance,
    add_items_from_file, get_user_balance_and_top_up, get_purchase_history,
    admin_add_new_category_db, update_user_balance_in_db, update_user_balance_after_buy,
    admin_delete_category, edit_cat_price_db, edit_cat_desc_db, edit_cat_name_db,
    admin_delete_category_db, is_payment_processed, save_payment_order,
    check_user
)

from .keyboards import (
    start_kb, admin_start_kb, buy_category_keyboard, add_category_keyboard,
    buy_buy_item, create_user_profile, top_up_cancel_kb,
    choose_payment, manage_category_keyboard, manage_one_cat
)

from aiocryptopay import AioCryptoPay


CRYPTO_PAY = AioCryptoPay(CRYPTO_BOT_TOKEN)
router = Router()
bot = Bot(BOT_TOKEN)
crypto_Bot = CRYPTO_BOT_TOKEN

# Состояния для FSM
class ItemStates(StatesGroup):
    category = State()
    file = State()
    quantity = State()

class CryptoPayment(StatesGroup):
    amount = State()

class LolzPayment(StatesGroup):
    amount = State()
    tg_id = State()
    order_id = State()

class OrderState(StatesGroup):
    choosing_payment = State()
    waiting_for_payment = State()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Userchange(StatesGroup):
    tg_id = State()
    new_balance = State()

class NewCategory(StatesGroup):
        name = State()
        desc = State()
        price = State()

class EditCategory(StatesGroup):
    cat_id = State()
    name = State()
    desc = State()
    price = State()


def get_main_menu_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="get_menu")]
    ])
def get_after_purchase_button(tg_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="get_menu")],
        [InlineKeyboardButton(text="Мои покупки", callback_data=f'history_{tg_id}')]
    ])
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    if await check_user(message.from_user.id):
        kb = await admin_start_kb(message.from_user.id) if message.from_user.id in ADMIN_LIST else await start_kb(message.from_user.id)
        await message.answer(
        f'👋 Привет, {message.from_user.first_name}, добро пожаловать в магазин! 🛍️\n'
        'Выбери действие в меню ниже:',
        reply_markup=kb
        )
    else:
        await message.answer('Перед началом использования бота требуется принять пользовательское соглашение.\nОзнакомиться с ним можно по этой ссылке: telegra.ph/Polzovatelskoe-soglashenie-03-16-12',
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                 [InlineKeyboardButton(text='Принять✅', callback_data='accept_agreements')]
                             ]))


@router.callback_query(F.data=='accept_agreements')
async def user_accept_agreements(callback: CallbackQuery):
    await callback.answer()
    await new_user(callback.from_user.id)
    kb = await admin_start_kb(callback.from_user.id) if callback.from_user.id in ADMIN_LIST else await start_kb(callback.from_user.id)
    await callback.message.edit_text(
        f'👋 Привет, {callback.from_user.first_name}, добро пожаловать в магазин! 🛍️\n'
        'Выбери действие в меню ниже:',
        reply_markup=kb
    )


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

@router.callback_query(F.data == 'items')
async def cmd_get_category(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        '📂 Выбери категорию товаров:',
        reply_markup=await buy_category_keyboard(await get_categories())
    )

@router.callback_query(F.data.startswith('choose_'))
async def cmd_buy_item(callback: CallbackQuery):
    try:
        await callback.answer()
        category_id = int(callback.data.split('_')[1])
        category_data = await get_category(category_id)
        
        if not category_data:
            await callback.message.answer("❌ Товар не найден.", reply_markup=get_main_menu_button())
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
        await callback.message.answer("⚠️ Ошибка. Попробуй позже.", reply_markup=get_main_menu_button())
        print(f"Ошибка в cmd_buy_item: {e}")

@router.callback_query(F.data.startswith('buy_'))
async def handle_buy_start(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        category_id = int(callback.data.split('_')[1])
        await state.update_data(category_id=category_id)
        await state.set_state(ItemStates.quantity)
        await callback.message.answer("🔢 Введи количество почт для покупки:")
    except Exception as e:
        await callback.message.answer("⚠️ Ошибка. Попробуй позже.", reply_markup=get_main_menu_button())
        print(f"Ошибка в handle_buy_start: {e}")

@router.message(ItemStates.quantity)
async def handle_buy_quantity(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        category_id = data.get('category_id')
        category = await get_category(category_id)
        user_tg_id = message.from_user.id
        
        if not message.text.isdigit():
            await message.answer("❌ Введи число!", reply_markup=get_main_menu_button())
            return
        
        quantity = int(message.text)
        if quantity <= 0:
            await message.answer("❌ Количество должно быть больше нуля!", reply_markup=get_main_menu_button())
            return
        
        available_items = await get_available_items(category_id, quantity)
        if len(available_items) < quantity:
            await message.answer(f"❌ Доступно только {len(available_items)} шт.", reply_markup=get_main_menu_button())
            return
        
        total_price = category.price * quantity
        user_balance = await get_user_balance(user_tg_id)
        if user_balance < total_price:
            await message.answer(f"❌ Недостаточно средств. Нужно: {total_price} руб.\nТвой баланс: {user_balance} руб.", reply_markup=get_main_menu_button())
            return
        
        await update_user_balance_after_buy(user_tg_id, -total_price)
        await create_purchases(user_tg_id, category_id, available_items)
        await delete_items(available_items)
        
        # Формируем данные для вывода
        items_info = "\n".join(
            f"{item.login}"
            for item in available_items
        )
        
        # Если почт меньше 5, добавляем данные в основное сообщение
        if quantity < 5:
            await message.answer(
                f"✅ Успешно куплено {quantity} шт.\n\n"
                f"💸 Списано: {total_price} руб.\n\n"
                f"📂 Категория: {category.name}\n\n"
                f"📦 Данные:\n\n{items_info}",
                reply_markup=get_after_purchase_button(user_tg_id)
            )
        else:  # Если почт больше или равно 5, отправляем данные отдельным сообщением
            await message.answer(
                f"✅ Успешно куплено {quantity} шт.\n\n"
                f"💸 Списано: {total_price} руб.\n\n"
                f"📂 Категория: {category.name}\n\n",
                reply_markup=get_after_purchase_button(user_tg_id)
            )
            await message.answer(
                f"📦 Данные:\n\n{items_info}"
            )
    
        await state.clear()
    except Exception as e:
        await message.answer("⚠️ Ошибка. Попробуй позже.", reply_markup=get_main_menu_button())
        print(f"Ошибка в handle_buy_quantity: {e}")

@router.callback_query(F.data == 'top_up')
async def add_items(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await state.clear()
        await state.set_state(ItemStates.category)
        await callback.message.edit_text(
            '📥 Выбери категорию для пополнения товаров:',
            reply_markup=await add_category_keyboard(await get_categories())
        )
    except Exception as e:
        await callback.message.answer("⚠️ Ошибка. Попробуй позже.", reply_markup=get_main_menu_button())
        print(f"Ошибка в add_items: {e}")

@router.callback_query(F.data.startswith('add_'))
async def add_items_2(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        category_id = callback.data.split('_')[1]
        await state.update_data(category_id=category_id)
        await state.set_state(ItemStates.file)
        await callback.message.answer('📤 Отправь текстовый файл с логинами (каждый логин на новой строке).')
    except Exception as e:
        await callback.message.answer("⚠️ Ошибка. Попробуй позже.", reply_markup=get_main_menu_button())

@router.message(ItemStates.file)
async def add_items_3(message: Message, state: FSMContext):
    try:
        if not message.document:
            await message.answer('📄 Пожалуйста, отправь текстовый файл.', reply_markup=get_main_menu_button())
            return

        data = await state.get_data()
        category_id = data.get('category_id')

        file_id = message.document.file_id
        file = await message.bot.get_file(file_id)
        file_path = file.file_path

        downloaded_file = await message.bot.download_file(file_path)
        file_content = downloaded_file.read().decode('utf-8')

        await add_items_from_file(category_id, file_content)
        await state.clear()
        await message.answer('✅ Товары успешно добавлены!', reply_markup=get_main_menu_button())
    except Exception as e:
        await message.answer("⚠️ Ошибка. Попробуй позже.", reply_markup=get_main_menu_button())

@router.callback_query(F.data.startswith('my_profile_'))
async def give_user_profile(callback: CallbackQuery):
    try:
        await callback.answer()
        tg_id = callback.data.split('_')[2]
        balance, top_up = await get_user_balance_and_top_up(tg_id)
        await callback.message.edit_text(
            f'💰 Ваш баланс: {balance} руб.\n'
            f'💳 Всего пополнено: {top_up} руб.\n'
            'Выбери действие:',
            reply_markup=await create_user_profile(callback.from_user.id)
        )
    except Exception as e:
        await callback.message.answer("⚠️ Ошибка. Попробуй позже.", reply_markup=get_main_menu_button())
        print(f"Ошибка в give_user_profile: {e}")

@router.callback_query(F.data.startswith('history_'))
async def cmd_profile_history(callback: CallbackQuery):
    try:
        await callback.answer()
        tg_id = int(callback.data.split('_')[1])
        purchase_history = await get_purchase_history(tg_id)
        
        if not purchase_history:
            await callback.message.answer("📜 История покупок пуста", reply_markup=get_main_menu_button())
            return
        
        response = "📜 История покупок:\n\n"
        for category, items in purchase_history.items():
            response += f"📂 Категория: {category}\n"
            for item in items:
                response += f"{item}\n"
            response += "\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Назад', callback_data=f'my_profile_{callback.from_user.id}')],
            [InlineKeyboardButton(text='🏠 Главное меню', callback_data='get_menu')]
        ])
        
        await callback.message.edit_text(response, reply_markup=keyboard)
    except Exception as e:
        await callback.message.answer("⚠️ Ошибка. Попробуй позже.", reply_markup=get_main_menu_button())
        print(f"Ошибка в cmd_profile_history: {e}")

@router.callback_query(F.data.startswith('top_up_'))
async def create_top_up(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text('💳 Выберите способ оплаты:',
                             reply_markup= await choose_payment(callback.from_user.id))
    await state.set_state(OrderState.waiting_for_payment)

@router.callback_query(F.data.startswith('lolz_'))
async def create_lolz_payment(callback: CallbackQuery, state: FSMContext):
    st = await state.get_state()
    if st != OrderState.choosing_payment:
        return
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
        await callback.message.answer("⚠️ Произошла ошибка. Попробуйте позже.", reply_markup=get_main_menu_button())

@router.message(LolzPayment.amount)
async def top_up_end(message: Message, state: FSMContext):
    try:
        if not message.text.isdigit():
            await message.answer("❌ Введите число!", reply_markup=get_main_menu_button())
            return
        
        amount = int(message.text)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше нуля!", reply_markup=get_main_menu_button())
            return
        
        order_id = os.urandom(15).hex()
        pay_url = LOLZ_TOKEN.get_payment_link(amount=amount, comment=order_id)
        await state.set_state(OrderState.waiting_for_payment)
        await message.answer(
            f'💳 Оплатите {amount} руб. по ссылке: {pay_url}\n\n'
            'После оплаты нажмите кнопку "Проверить оплату".',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_lolz_payment_{order_id}_{amount}"),
                InlineKeyboardButton(text="❌ Отмена оплаты", callback_data="cancel_payment")]
            ])
        )
    except Exception as e:
        logger.error(f"Ошибка в top_up_end: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.", reply_markup=get_main_menu_button())


@router.callback_query(F.data.startswith('check_lolz_payment_'))
async def check_lolz_payment(callback: CallbackQuery, state: FSMContext):
    st = await state.get_state()
    if st != OrderState.waiting_for_payment:
        return
    try:
        await callback.answer()

        order_id = callback.data.split('_')[3]
        amount = int(callback.data.split('_')[4])
        tg_id = callback.from_user.id

        async with async_session() as session:  # Используем async_session
            # Проверяем, был ли платеж уже обработан
            if await is_payment_processed(session, order_id):
                await callback.message.answer("✅ Платеж уже был обработан.", reply_markup=get_main_menu_button())
                return

            payment_info = await LOLZ_TOKEN.check_status_payment(amount, comment=str(order_id))
            if payment_info:
                # Сохраняем order_id в базу данных
                if await save_payment_order(session, order_id):
                    await update_user_balance(tg_id, amount)
                    await callback.message.answer(
                        f"✅ Платеж подтвержден! \nСумма: {amount} руб.\n\n"
                        f"Ваш баланс успешно пополнен. 🎉",
                        reply_markup=get_main_menu_button()
                    )
                else:
                    await callback.message.answer("❌ Ошибка при обработке платежа.", reply_markup=get_main_menu_button())
            else:
                await callback.message.answer("❌ Платеж не найден. Попробуйте позже.", reply_markup=get_main_menu_button())
    except Exception as e:
        logger.error(f"Ошибка в check_lolz_payment: {e}")
        await callback.message.answer("⚠️ Произошла ошибка. Попробуйте позже.", reply_markup=get_main_menu_button())



@router.callback_query(F.data.startswith('check_crypto_payment_'))
async def check_crypto_payment(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()

        order_id = callback.data.split('_')[3]
        amount = int(callback.data.split('_')[4])
        tg_id = callback.from_user.id

        async with async_session() as session:
            if await is_payment_processed(session, order_id):
                await callback.message.answer("✅ Платеж уже был обработан.", reply_markup=get_main_menu_button())
                return

            invoices = await crypto_Bot.get_invoices(invoice_ids=[order_id], count=1)
            if invoices:
                invoice = invoices[0]
                if invoice.paid_at is not None and invoice.status != "active":
                    if await save_payment_order(session, order_id):
                        await update_user_balance(tg_id, amount)
                        await callback.message.answer(
                            f"✅ Оплата подтверждена! \n\n"
                            f"💳 Сумма пополнения: {str(amount)} RUB\n"
                            f"Ваш баланс успешно пополнен. 🎉",
                            reply_markup=get_main_menu_button()
                        )
                    else:
                        await callback.message.answer("❌ Ошибка при обработке платежа.", reply_markup=get_main_menu_button())
                else:
                    await callback.message.answer("❌ Оплата не найдена или не завершена")
            else:
                await callback.message.answer("❌ Оплата не найдена")
    except Exception as e:
        logger.error(f"Ошибка в check_crypto_payment: {e}")
        await callback.message.answer(f"❗️ Ошибка проверки оплаты: {str(e)}",
                                      reply_markup=get_main_menu_button())

@router.callback_query(F.data.startswith('crypto_'))
async def top_up_user_balance_crypto(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await state.clear()
        await callback.message.edit_text(
            '💳 Введите желаемую сумму пополнения в рублях:',
            reply_markup=await top_up_cancel_kb(callback.from_user.id)
        )
        await state.set_state(CryptoPayment.amount)
    except Exception as e:
        logger.error(f"Ошибка в top_up_user_balance_crypto: {e}")
        await callback.message.answer("⚠️ Произошла ошибка. Попробуйте позже.", reply_markup=get_main_menu_button())

@router.message(CryptoPayment.amount)
async def top_up_end_crypto(message: Message, state: FSMContext):
    try:
        if not message.text.isdigit():
            await message.answer("❌ Введите число!", reply_markup=get_main_menu_button())
            return
        
        amount = int(message.text)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше нуля!", reply_markup=get_main_menu_button())
            return
        await state.clear()
        order = await crypto_Bot.create_invoice(amount / USD_RUB_COURSE, currency_type="crypto", asset="USDT")

        pay_url = order.pay_url
        order_id = order.invoice_id
        await message.answer(
            f"💳 Оплатите {amount / USD_RUB_COURSE} USDT по ссылке:\n{pay_url}\n"
            "После оплаты нажмите кнопку ниже:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_crypto_payment_{order_id}_{amount}"),
                    InlineKeyboardButton(text="❌ Отмена оплаты", callback_data="cancel_payment")
                ]
            ])
        )
    except Exception as e:
        logger.error(f"Ошибка в top_up_end_crypto: {e}")
        await message.answer(f"❗️ Ошибка: {str(e)}")

# Обработчик для отмены оплаты
@router.callback_query(F.data == 'cancel_payment')
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer(
        "❌ Оплата отменена.",
                                      reply_markup=  get_main_menu_button()
    )

@router.callback_query(F.data == 'big_catalog')
async def get_big_catalog(callback: CallbackQuery):
    try:
        await callback.answer()
        categories = await get_categories()
        response = "📂 Каталог товаров:\n\n"
        
        for category in categories:
            items = await get_available_items(category.id, 1000)  # Получаем все доступные товары в категории
            if items:  # Если есть товары в категории
                response += f"{category.name} ({len(items)} почт):\n"
                for item in items:
                    response += f"{item.login}\n"
                response += "\n"
        
        if response == "📂 Каталог товаров:\n\n":  # Если ни в одной категории нет товаров
            response = "📭 В каталоге пока нет доступных товаров.\nМеню - /start"
        
        await callback.message.edit_text(response, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Назад', callback_data='get_menu')]
        ]))
    except Exception as e:
        await callback.message.answer("⚠️ Ошибка. Попробуй позже.",
                                      reply_markup= get_main_menu_button())
        print(f"Ошибка в get_big_catalog: {e}")

@router.callback_query(F.data == 'change_balance')
async def change_user_balance(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Userchange.tg_id)
    await callback.message.edit_text(
        "Введите уникальный телеграм id пользователя, которому вы хотите поменять баланс",
        reply_markup=get_main_menu_button()
    )

@router.message(Userchange.tg_id)
async def process_tg_id(message: Message, state: FSMContext):
    try:
        tg_id = int(message.text)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректный ID (число).")
        return

    await state.update_data(tg_id=tg_id)
    await state.set_state(Userchange.new_balance)

    user_balance = await get_user_balance(tg_id)
    await message.answer(f'💰 Баланс данного пользователя: {user_balance}\nВведите новое значение:')

@router.message(Userchange.new_balance)
async def set_new_user_balance(message: Message, state: FSMContext):
    try:
        new_balance = int(message.text)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное значение баланса (число).")
        return

    data = await state.get_data()
    tg_id = data['tg_id']

    if await update_user_balance_in_db(tg_id, new_balance):
        await message.answer('✅ Новый баланс для пользователя успешно установлен!', reply_markup=get_main_menu_button())
    else:
        await message.answer('❌ Не удалось изменить баланс, вероятно, такого пользователя не существует', reply_markup=get_main_menu_button())

    await state.clear()

@router.callback_query(F.data=='manage_categories')
async def admin_manage_cat(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text('📁 Выберите категорию для управления, или добавьте новую', 
                                    reply_markup=await manage_category_keyboard(await get_categories()))

@router.callback_query(F.data=='new_category')
async def add_new_category(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(NewCategory.name)
    await callback.message.edit_text('✏️ Введите имя для новой категории: ')

@router.message(NewCategory.name)
async def handle_new_category_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(NewCategory.desc)
    await message.answer('📝 Введите описание для категории: ')

@router.message(NewCategory.desc)
async def handle_new_category_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await state.set_state(NewCategory.price)
    await message.answer('💵 Введите цену (за одну почту) для категории: ')

@router.message(NewCategory.price)
async def handle_new_category_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer('❌ Пожалуйста, введите число')
        return
    
    await state.update_data(price=message.text)
    data = await state.get_data()
    name, desc, price = data['name'], data['desc'], data['price']
    if await admin_add_new_category_db(name, desc, int(price)):
        await message.answer(f'✅ Категория под названием {name} успешно добавлена',
                             reply_markup=get_main_menu_button())

@router.callback_query(F.data.startswith('manage_category_'))
async def admin_manage_category_admin(callback: CallbackQuery):
    category_id = int(callback.data.split('_')[2])
    await callback.answer()
    category = await get_category(category_id)
    await callback.message.edit_text(f'📁 Имя: {category.name}\n📝 Описание: {category.desc}\n💵 Цена: {category.price}\nВыберите действие для данной категории',
                                     reply_markup=await manage_one_cat(int(category_id)))


@router.callback_query(F.data.startswith('delete_cat_data_'))
async def delete_category_by_id_admin(callback: CallbackQuery):
    try:
        await callback.answer()
        category_id = int(callback.data.split('_')[3])
        result = await admin_delete_category_db(category_id)
        
        if result:
            await callback.message.answer(
                '❌ Не удалось удалить содержимое категории\nВероятно, она уже была пуста',
                reply_markup=get_main_menu_button()
            )
        else:
            await callback.message.answer(
                '✅ Содержимое категории успешно удалено!',
                reply_markup=get_main_menu_button()
            )
    except Exception as e:
        logger.error(f"Ошибка в delete_category_by_id_admin: {e}")
        await callback.message.answer(
            "⚠️ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_main_menu_button()
        )


@router.callback_query(F.data.startswith('delete_cat_'))
async def delete_category_by_id_admin(callback: CallbackQuery):
    try:
        await callback.answer()
        category_id = int(callback.data.split('_')[2])
        
        result = await admin_delete_category(category_id)
        
        if not result:
            await callback.message.answer(
                '❌ Не удалось удалить категорию',
                reply_markup=get_main_menu_button()
            )
        else:
            await callback.message.answer(
                '✅ Категория успешно удалена!',
                reply_markup=get_main_menu_button()
            )
    except Exception as e:
        logger.error(f"Ошибка в delete_category_by_id_admin: {e}")
        await callback.message.answer(
            "⚠️ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_main_menu_button()
        )


@router.callback_query(F.data.startswith('cat_change_'))
async def change_cat_params(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    operation = callback.data.split('_')[2]
    cat_id = callback.data.split('_')[3]
    await state.set_state(EditCategory.cat_id)
    await state.update_data(cat_id=cat_id)
    if operation == 'name':
        await state.set_state(EditCategory.name)
        await callback.message.edit_text('✏️ Введите имя для данной категории: ')
    elif operation == 'desc':
        await state.set_state(EditCategory.desc)
        await callback.message.edit_text('📝 Введите описание для данной категории: ')
    elif operation == 'price':
        await state.set_state(EditCategory.price)
        await callback.message.edit_text('💵 Введите цену для данной категории: ')

@router.message(EditCategory.name)
async def admin_edit_category_name_admin(message: Message, state: FSMContext):
    name = message.text
    data = await state.get_data()
    cat_id = data['cat_id']
    await state.clear()
    if await edit_cat_name_db(name, cat_id):
        await message.answer(f'✅ Имя успешно изменено',
                             reply_markup=get_main_menu_button())
    else:
        await message.answer(f'❌ Не удалось изменить имя',
                             reply_markup=get_main_menu_button())
        
@router.message(EditCategory.desc)
async def admin_edit_category_desc_admin(message: Message, state: FSMContext):
    desc = message.text
    data = await state.get_data()
    cat_id = data['cat_id']
    await state.clear()
    if await edit_cat_desc_db(desc, cat_id):
        await message.answer(f'✅ Описание успешно изменено',
                             reply_markup=get_main_menu_button())
    else:
        await message.answer(f'❌ Не удалось изменить описание',
                             reply_markup=get_main_menu_button())

@router.message(EditCategory.price)
async def admin_edit_category_price_admin(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer('❌ Пожалуйста, введите число')
    price = int(message.text)
    data = await state.get_data()
    cat_id = data['cat_id']
    await state.clear()
    if await edit_cat_price_db(price, cat_id):
        await message.answer(f'✅ Цена успешно изменена',
                             reply_markup=get_main_menu_button())
    else:
        await message.answer(f'❌ Не удалось изменить цену',
                             reply_markup=get_main_menu_button())


