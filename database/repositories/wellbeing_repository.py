"""Репозиторий для работы с самочувствием."""
from datetime import date
from typing import Optional

from database.models import WellbeingEntry
from database.session import get_db_session


class WellbeingRepository:
    """Репозиторий для отметок самочувствия."""

    @staticmethod
    def save_quick_entry(
        user_id: str,
        mood: str,
        influence: str,
        difficulty: Optional[str],
        entry_date: date,
    ) -> int:
        """Сохраняет быстрый опрос."""
        with get_db_session() as session:
            entry = WellbeingEntry(
                user_id=str(user_id),
                entry_type="quick",
                mood=mood,
                influence=influence,
                difficulty=difficulty,
                date=entry_date,
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry.id

    @staticmethod
    def save_comment_entry(user_id: str, comment: str, entry_date: date) -> int:
        """Сохраняет комментарий о самочувствии."""
        with get_db_session() as session:
            entry = WellbeingEntry(
                user_id=str(user_id),
                entry_type="comment",
                comment=comment,
                date=entry_date,
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry.id
