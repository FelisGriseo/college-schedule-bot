from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import Base


class Database:
    def __init__(self, url: str) -> None:
        self.engine = create_async_engine(url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_tables(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            columns = await connection.exec_driver_sql("PRAGMA table_info(replacements)")
            names = {row[1] for row in columns.fetchall()}
            if "match_status" not in names:
                await connection.exec_driver_sql(
                    "ALTER TABLE replacements ADD COLUMN match_status VARCHAR(20) NOT NULL DEFAULT 'matched'"
                )

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            yield session

    async def close(self) -> None:
        await self.engine.dispose()
