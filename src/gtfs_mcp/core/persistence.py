"""SQLite persistence for parsed GTFS feed data.

Every parsed row (stops, routes, trips, stop_times, calendar, calendar_dates,
agencies, feed_info) is stored as a JSON blob keyed by feed_id + table, with
its original file order preserved. On restart the feed manager restores feeds
from this store instead of re-downloading.

The store lives at ``<data_dir>/gtfs_mcp.db`` - separate from the registry
database (db/database.py) on purpose: it follows the feed data directory, which
is per-user writable in the frozen desktop app.
"""

import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import JSON, DateTime, Integer, String, delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

logger = logging.getLogger(__name__)

# Table -> primary-key column used for the row_key (ordering stability fallback)
_KEY_FOR: dict[str, str] = {
    "stops": "stop_id",
    "routes": "route_id",
    "trips": "trip_id",
    "stop_times": "stop_id",
    "calendar": "service_id",
    "calendar_dates": "service_id",
    "agencies": "agency_id",
    "feed_info": "feed_publisher_name",
}


class _Base(DeclarativeBase):
    pass


class FeedRow(_Base):
    __tablename__ = "feed_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feed_id: Mapped[str] = mapped_column(String(100), index=True)
    table_name: Mapped[str] = mapped_column(String(50))
    row_key: Mapped[str] = mapped_column(String(255))
    row_json: Mapped[dict] = mapped_column(JSON)
    ord: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime)


class FeedSnapshot(_Base):
    __tablename__ = "feed_snapshots"

    feed_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    url: Mapped[str] = mapped_column(String(512))
    fetched_at: Mapped[datetime] = mapped_column(DateTime)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    tables: Mapped[dict] = mapped_column(JSON, default=dict)


class GTFSPersistence:
    """Async SQLite store for parsed GTFS feed rows."""

    _initialized: bool = False

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path}")
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    async def init(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(_Base.metadata.create_all)

    async def save_feed(self, feed_id: str, url: str, rows: dict[str, list[dict]]) -> int:
        """Replace all stored rows for a feed with the given parsed tables."""
        now = datetime.utcnow()
        count = 0
        tables: dict[str, int] = {}
        async with self._session_factory() as session:
            await session.execute(delete(FeedRow).where(FeedRow.feed_id == feed_id))
            for table, items in rows.items():
                tables[table] = len(items)
                key_col = _KEY_FOR.get(table, "id")
                for i, item in enumerate(items):
                    key = str(item.get(key_col, "") or f"row-{i}")
                    session.add(
                        FeedRow(
                            feed_id=feed_id,
                            table_name=table,
                            row_key=key,
                            row_json=item,
                            ord=i,
                            fetched_at=now,
                        )
                    )
                    count += 1
            snap = await session.get(FeedSnapshot, feed_id)
            if snap is None:
                session.add(
                    FeedSnapshot(
                        feed_id=feed_id,
                        url=url,
                        fetched_at=now,
                        row_count=count,
                        tables=tables,
                    )
                )
            else:
                snap.url = url
                snap.fetched_at = now
                snap.row_count = count
                snap.tables = tables
            await session.commit()
        logger.info("Persisted %d rows for feed %s", count, feed_id)
        return count

    async def load_feed(self, feed_id: str) -> tuple[dict[str, list[dict]], FeedSnapshot] | None:
        """Return (rows_by_table, snapshot) for a feed, or None if not stored."""
        async with self._session_factory() as session:
            snap = await session.get(FeedSnapshot, feed_id)
            if snap is None:
                return None
            result = await session.execute(
                select(FeedRow).where(FeedRow.feed_id == feed_id).order_by(FeedRow.table_name, FeedRow.ord)
            )
            rows: dict[str, list[dict]] = {}
            for row in result.scalars():
                rows.setdefault(row.table_name, []).append(row.row_json)
            return rows, snap

    async def list_snapshots(self) -> list[dict]:
        """List stored feed snapshots (feed_id, url, fetched_at, counts)."""
        async with self._session_factory() as session:
            result = await session.execute(select(FeedSnapshot).order_by(FeedSnapshot.feed_id))
            return [
                {
                    "feed_id": s.feed_id,
                    "url": s.url,
                    "fetched_at": s.fetched_at.isoformat() if s.fetched_at else None,
                    "row_count": s.row_count,
                    "tables": s.tables,
                }
                for s in result.scalars()
            ]

    async def close(self) -> None:
        await self._engine.dispose()
