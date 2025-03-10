from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from .models import (
    async_session,
    User,
    Category,
    Item,
    Purchase
)
from datetime import datetime, timedelta
from config import LOLZ_TOKEN

async def new_user(tg_id: int) -> None:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            user = User(tg_id=tg_id, balance=0, total_top_up=0)
            session.add(user)
            await session.commit()

async def get_categories() -> list[Category]:
    async with async_session() as session:
        result = await session.scalars(select(Category))
        return result.all()

async def get_category(category_id: int) -> Category | None:
    async with async_session() as session:
        return await session.scalar(select(Category).where(Category.id == category_id))

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

async def update_user_balance(tg_id: int, delta: int) -> None:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.balance += delta
            await session.commit()

async def get_user_balance(tg_id: int) -> int:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user.balance if user else 0
    
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

