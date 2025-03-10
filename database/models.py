from sqlalchemy import String, Integer, ForeignKey, select
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
    
    # Связь с товарами
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
    balance = mapped_column(Integer, default=100)
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


async def init_categories():
    async with async_session() as session:
        # Проверяем, есть ли уже категории в таблице
        existing_categories = await session.scalars(select(Category))
        if not existing_categories.first():  # Если таблица пуста
            categories = [
                Category(name='Vkontakte', desc='Почты Вконтакте', price=10),
                Category(name='Google', desc='Почты Google', price=1),
                Category(name='Yandex', desc='Почты Yandex', price=12),
                Category(name='Mail.ru', desc='Почты Mail.ru', price=8),
                Category(name='Facebook', desc='Почты Facebook', price=20),
            ]
            session.add_all(categories)
            await session.commit()


async def async_main():
    async with engine.begin() as conn:
        # Создаем таблицы, если они не существуют
        await conn.run_sync(Base.metadata.create_all)
        
        # Добавляем категории, если таблица categories пуста
        await init_categories()
        