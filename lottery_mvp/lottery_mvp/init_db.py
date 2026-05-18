from __future__ import annotations

from db.database import get_connection
from db.schema import AI_ANALYSIS_CACHE_SCHEMA, DLT_SCHEMA, SSQ_SCHEMA, UPDATE_LOG_SCHEMA


SSQ_SAMPLE_ROWS = [
    ("2026048", "2026-04-26", "03,09,14,18,27,31", 12, 378000000.0),
    ("2026049", "2026-04-28", "01,06,13,22,28,33", 7, 381000000.0),
    ("2026050", "2026-05-01", "04,07,16,19,24,30", 2, 360000000.0),
    ("2026051", "2026-05-03", "05,08,12,17,25,32", 16, 355000000.0),
    ("2026052", "2026-05-05", "02,10,11,20,29,33", 6, 372000000.0),
    ("2026053", "2026-05-08", "03,06,15,18,26,31", 9, 389000000.0),
    ("2026054", "2026-05-10", "01,07,14,21,27,30", 11, 366000000.0),
    ("2026055", "2026-05-12", "04,09,16,22,28,32", 5, 374000000.0),
    ("2026056", "2026-05-14", "02,08,13,17,25,29", 14, 381200000.0),
    ("2026057", "2026-05-17", "05,10,12,19,24,31", 3, 393500000.0),
]


DLT_SAMPLE_ROWS = [
    ("2026046", "2026-04-25", "04,11,19,28,35", "03,09", 286000000.0),
    ("2026047", "2026-04-27", "01,08,17,24,33", "04,12", 291000000.0),
    ("2026048", "2026-04-29", "06,09,14,22,31", "02,08", 279000000.0),
    ("2026049", "2026-05-02", "03,12,18,27,34", "01,11", 283000000.0),
    ("2026050", "2026-05-04", "05,10,21,29,32", "06,10", 295000000.0),
    ("2026051", "2026-05-06", "02,07,16,25,30", "05,09", 288000000.0),
    ("2026052", "2026-05-09", "08,13,20,26,35", "04,07", 297500000.0),
    ("2026053", "2026-05-11", "01,11,19,23,31", "03,12", 302000000.0),
    ("2026054", "2026-05-13", "06,15,22,28,34", "02,06", 289300000.0),
    ("2026055", "2026-05-16", "04,09,17,24,33", "01,08", 305800000.0),
]


def initialize_database() -> None:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(SSQ_SCHEMA)
        cursor.execute(DLT_SCHEMA)
        cursor.execute(UPDATE_LOG_SCHEMA)
        cursor.execute(AI_ANALYSIS_CACHE_SCHEMA)
        _ensure_columns(cursor, "ssq_draws", ["prize_pool", "source_url", "updated_at"])
        _ensure_columns(cursor, "dlt_draws", ["prize_pool", "source_url", "updated_at"])
        _ensure_columns(cursor, "update_logs", ["run_id", "trigger_source"])

        ssq_count = cursor.execute("SELECT COUNT(*) FROM ssq_draws").fetchone()[0]
        if ssq_count == 0:
            cursor.executemany(
                """
                INSERT INTO ssq_draws (
                    issue, draw_date, red_numbers, blue_number, sales_amount, prize_pool, source_url
                )
                VALUES (?, ?, ?, ?, ?, NULL, 'sample')
                """,
                SSQ_SAMPLE_ROWS,
            )

        dlt_count = cursor.execute("SELECT COUNT(*) FROM dlt_draws").fetchone()[0]
        if dlt_count == 0:
            cursor.executemany(
                """
                INSERT INTO dlt_draws (
                    issue, draw_date, front_numbers, back_numbers, sales_amount, prize_pool, source_url
                )
                VALUES (?, ?, ?, ?, ?, NULL, 'sample')
                """,
                DLT_SAMPLE_ROWS,
            )

        connection.commit()


def _ensure_columns(cursor, table_name: str, column_names: list[str]) -> None:
    existing_columns = {
        row[1]
        for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    }

    statements = {
        "prize_pool": f"ALTER TABLE {table_name} ADD COLUMN prize_pool REAL",
        "source_url": f"ALTER TABLE {table_name} ADD COLUMN source_url TEXT",
        "updated_at": f"ALTER TABLE {table_name} ADD COLUMN updated_at TEXT",
        "run_id": f"ALTER TABLE {table_name} ADD COLUMN run_id TEXT",
        "trigger_source": f"ALTER TABLE {table_name} ADD COLUMN trigger_source TEXT DEFAULT 'system'",
    }

    for column_name in column_names:
        if column_name not in existing_columns:
            cursor.execute(statements[column_name])
