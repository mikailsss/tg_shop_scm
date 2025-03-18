from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from .models import (
    async_session,
    User,
    Category,
    Item,
    Purchase,
    ProcessedPayment
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

async def save_payment_order(session, order_id: str) -> bool:
  
    try:
        payment = ProcessedPayment(order_id=order_id, is_processed=True)
        session.add(payment)
        await session.commit()
        return True
    except IntegrityError:
        await session.rollback()
        return False  # Если order_id уже существует

async def is_payment_processed(session, order_id: str) -> bool:
    result = await session.scalar(select(ProcessedPayment).where(ProcessedPayment.order_id == order_id))
    return result is not None


async def new_user(tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            user = User(tg_id=tg_id, balance=0, total_top_up=0)
            session.add(user)
            await session.commit()
            
async def check_user(tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            return False
        return True

async def get_categories():
    async with async_session() as session:
        result = await session.scalars(select(Category))
        return result.all()

async def get_category(category_id: int):
    async with async_session() as session:
        return await session.scalar(select(Category).where(Category.id == category_id))

async def admin_add_new_category_db(name, desc, price):
    async with async_session() as session:
        try:
            new_category = Category(name=name, desc=desc, price=price)
            session.add(new_category)
            await session.commit()
            return True
        except Exception as e:
            print(f'Ошибка в admin_add_new_category_db\n{e}')
            return False



async def admin_delete_category(cat_id: int):
    async with async_session() as session:
        try:
            items_to_delete = await session.scalars(select(Item).where(Item.category_id == cat_id))
            items_list = items_to_delete.all()  
                
            if items_list:  
                for item in items_list:
                    await session.delete(item)
                    
                    await session.commit()

            category = await session.scalar(select(Category).where(Category.id == cat_id)) 
            await session.delete(category)
            await session.commit()
            return True    

        except Exception as e:
            print(f'Ошибка\n{e}')
            return False



async def get_available_items(category_id: int, limit: int) -> list[Item]:
    async with async_session() as session:
        result = await session.scalars(
            select(Item)
            .where(Item.category_id == category_id)
            .limit(limit)
        )
        return result.all()

async def create_purchases(user_id: int, category_id: int, items: list[Item]) -> None:
    async with async_session() as session:
        for item in items:
            purchase = Purchase(
                buyer_id=user_id,
                category_id=category_id,
                login=item.login,
            )
            session.add(purchase)
        await session.commit()

async def delete_items(items: list[Item]) -> None:
    async with async_session() as session:
        for item in items:
            await session.execute(delete(Item).where(Item.id == item.id))
        await session.commit()

async def update_user_balance_after_buy(tg_id: int, delta: int) -> None:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.balance += delta
            await session.commit()

async def update_user_balance_in_db(tg_id: int, new_balance: int) -> bool:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            return False

        try:
            user.balance = new_balance
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении баланса: {e}")
            await session.rollback()
            return False

async def get_user_balance(tg_id: int) -> int:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user.balance if user.balance else 0
    
async def get_user_balance_and_top_up(tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user.balance, user.total_top_up

async def get_user_by_tg_id(tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user.id

async def add_items_from_file(category_id: int, file_content: str) -> None:
    async with async_session() as session:
        for line in file_content.splitlines():
            if line.strip():
                login = line.strip()
                item = Item(
                    category_id=category_id,
                    login=login,
                    )
                session.add(item)
        await session.commit()

async def get_user_profile(tg_id: int) -> User | None:
    async with async_session() as session:
        return await session.scalar(select(User).where(User.tg_id == tg_id))

async def get_purchase_history(user_id: int):
    async with async_session() as session:
        result = await session.scalars(
            select(Purchase)
            .where(Purchase.buyer_id == user_id)
            .options(selectinload(Purchase.category))
        )
        purchases = result.all()
        
        grouped_purchases = {}
        for purchase in purchases:
            category_name = purchase.category.name
            item_info = f"{purchase.login}"
            
            if category_name not in grouped_purchases:
                grouped_purchases[category_name] = []
            grouped_purchases[category_name].append(item_info)
        
        return grouped_purchases
    
async def update_user_balance(tg_id: int, amount: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.balance += amount
            user.total_top_up += amount
            await session.commit()


async def edit_cat_name_db(name, cat_id):
    async with async_session() as session:
        try:
            category = await session.scalar(select(Category).where(Category.id == cat_id))
            category.name = name 
            await session.commit()
            return True
        except Exception as e:
            print(f'Ошибка в edit_cat_name_db\n{e}')
            return False
        
async def edit_cat_desc_db(desc, cat_id):
    async with async_session() as session:
        try:
            category = await session.scalar(select(Category).where(Category.id == cat_id))
            category.desc = desc 
            await session.commit()
            return True
        except Exception as e:
            print(f'Ошибка в edit_cat_desc_db\n{e}')
            return False
        
async def edit_cat_price_db(price, cat_id):
    async with async_session() as session:
        try:
            category = await session.scalar(select(Category).where(Category.id == cat_id))
            category.price = price 
            await session.commit()
            return True
        except Exception as e:
            print(f'Ошибка в edit_cat_price_db\n{e}')
            return False

async def admin_delete_category_db(cat_id):
    async with async_session() as session:
        try:
            items_to_delete = await session.scalars(select(Item).where(Item.category_id == cat_id))
            items_list = items_to_delete.all()  
                
            if items_list:  
                for item in items_list:
                    await session.delete(item)
                    
                    await session.commit()

        except Exception as e:
            print(f'Ошибка\n{e}')
            return False