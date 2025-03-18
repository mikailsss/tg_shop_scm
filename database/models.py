from sqlalchemy import String, Integer, ForeignKey, select, Boolean
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Category(Base):
    __tablename__ = 'categories'
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String, unique=True)
    desc = mapped_column(String)
    price = mapped_column(Integer)
    image_url = mapped_column(String, nullable=True)
    items = relationship('Item', back_populates='category')
    
    # Связь с покупками
    purchases = relationship('Purchase', back_populates='category') # Связь с товарами


class Item(Base):
    __tablename__ = 'items'
    
    id = mapped_column(Integer, primary_key=True)  
    category_id = mapped_column(Integer, ForeignKey('categories.id'))  
    login = mapped_column(String)
    
    category = relationship('Category', back_populates='items')


class User(Base):
    __tablename__ = 'users'
    id = mapped_column(Integer, primary_key=True)
    tg_id = mapped_column(Integer) 
    balance = mapped_column(Integer, default=0)
    total_top_up = mapped_column(Integer, default=0)

    purchases = relationship('Purchase', back_populates='buyer')

class Purchase(Base):
    __tablename__ = 'purchases'
    id = mapped_column(Integer, primary_key=True)  
    buyer_id = mapped_column(Integer, ForeignKey('users.id'))
    category_id = mapped_column(Integer, ForeignKey('categories.id'))  # Ссылка на категорию
    login = mapped_column(String)

    
    # Связь с пользователем
    buyer = relationship('User', back_populates='purchases')
    
    # Связь с категорией
    category = relationship('Category', back_populates='purchases')


class ProcessedPayment(Base):
    __tablename__ = 'processed_payments'
    id = mapped_column(Integer, primary_key=True)
    order_id = mapped_column(String, unique=True, nullable=False)  # Уникальный идентификатор платежа
    is_processed = mapped_column(Boolean, default=False) 


async def async_main():
    async with engine.begin() as conn:
        # Создаем таблицы, если они не существуют
        await conn.run_sync(Base.metadata.create_all)
        

        