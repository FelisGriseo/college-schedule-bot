import unittest
from datetime import date

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from database.crud import upsert_replacement
from database.models import Base


class UpsertReplacementGroupNormalizationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_upsert_replacement_normalizes_group_name(self) -> None:
        async with self.session_factory() as session:
            replacement, is_latest = await upsert_replacement(
                session,
                {
                    "replacement_date": date(2026, 9, 22),
                    "group_name": "ME-251",
                    "pair_number": 1,
                    "new_subject": "Математика",
                    "teacher": "Іваненко",
                    "room": "101",
                    "note": None,
                    "source_message_id": 10,
                    "source_text": "test",
                },
            )

        self.assertTrue(is_latest)
        self.assertEqual(replacement.group_name, "МЕ-251")

    async def test_upsert_deduplicates_group_separator_variants(self) -> None:
        values = {
            "replacement_date": date(2026, 9, 22),
            "pair_number": 1,
            "new_subject": "Математика",
            "teacher": None,
            "room": None,
            "note": None,
            "source_message_id": 10,
            "source_text": "test",
        }
        async with self.session_factory() as session:
            first, _ = await upsert_replacement(session, {**values, "group_name": "ПОШ-123"})
            second, _ = await upsert_replacement(
                session, {**values, "group_name": "ПОШ123", "source_message_id": 11}
            )

        self.assertEqual(first.id, second.id)
        self.assertEqual(second.group_name, "ПОШ-123")


if __name__ == "__main__":
    unittest.main()
