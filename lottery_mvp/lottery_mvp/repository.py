from __future__ import annotations

from typing import Any

import pandas as pd

from db.database import get_connection


LOTTERY_TABLES = {
    "ssq": "ssq_draws",
    "dlt": "dlt_draws",
}


def load_recent_draws(lottery_type: str, limit: int = 30) -> pd.DataFrame:
    table_name = LOTTERY_TABLES[lottery_type]
    query = f"SELECT * FROM {table_name} ORDER BY draw_date DESC LIMIT ?"
    with get_connection() as connection:
        return pd.read_sql_query(query, connection, params=(limit,))


def search_draws(
    lottery_type: str,
    issue: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 30,
) -> pd.DataFrame:
    table_name = LOTTERY_TABLES[lottery_type]
    clauses: list[str] = []
    params: list[Any] = []

    if issue:
        clauses.append("issue = ?")
        params.append(issue)
    if start_date:
        clauses.append("draw_date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("draw_date <= ?")
        params.append(end_date)

    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)

    query = f"""
        SELECT *
        FROM {table_name}
        {where_sql}
        ORDER BY draw_date DESC
        LIMIT ?
    """
    params.append(limit)

    with get_connection() as connection:
        return pd.read_sql_query(query, connection, params=params)


def get_latest_issue(lottery_type: str) -> str | None:
    table_name = LOTTERY_TABLES[lottery_type]
    query = f"SELECT issue FROM {table_name} ORDER BY draw_date DESC, issue DESC LIMIT 1"
    with get_connection() as connection:
        row = connection.execute(query).fetchone()
    if row is None:
        return None
    return str(row["issue"])


def issue_exists(lottery_type: str, issue: str) -> bool:
    table_name = LOTTERY_TABLES[lottery_type]
    with get_connection() as connection:
        row = connection.execute(
            f"SELECT 1 FROM {table_name} WHERE issue = ? LIMIT 1",
            (issue,),
        ).fetchone()
    return row is not None


def upsert_ssq_draw(record: dict[str, Any]) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO ssq_draws (
                issue, draw_date, red_numbers, blue_number, sales_amount, prize_pool, source_url, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(issue) DO UPDATE SET
                draw_date = excluded.draw_date,
                red_numbers = excluded.red_numbers,
                blue_number = excluded.blue_number,
                sales_amount = excluded.sales_amount,
                prize_pool = excluded.prize_pool,
                source_url = excluded.source_url,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                record["issue"],
                record["draw_date"],
                record["red_numbers"],
                record["blue_number"],
                record.get("sales_amount"),
                record.get("prize_pool"),
                record.get("source_url"),
            ),
        )
        connection.commit()


def upsert_dlt_draw(record: dict[str, Any]) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO dlt_draws (
                issue, draw_date, front_numbers, back_numbers, sales_amount, prize_pool, source_url, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(issue) DO UPDATE SET
                draw_date = excluded.draw_date,
                front_numbers = excluded.front_numbers,
                back_numbers = excluded.back_numbers,
                sales_amount = excluded.sales_amount,
                prize_pool = excluded.prize_pool,
                source_url = excluded.source_url,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                record["issue"],
                record["draw_date"],
                record["front_numbers"],
                record["back_numbers"],
                record.get("sales_amount"),
                record.get("prize_pool"),
                record.get("source_url"),
            ),
        )
        connection.commit()


def create_update_log(
    lottery_type: str,
    status: str,
    issue: str | None = None,
    source_url: str | None = None,
    message: str | None = None,
    run_id: str | None = None,
    trigger_source: str = "system",
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO update_logs (lottery_type, issue, run_id, trigger_source, status, source_url, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (lottery_type, issue or "-", run_id, trigger_source, status, source_url, message),
        )
        connection.execute(
            """
            DELETE FROM update_logs
            WHERE id NOT IN (
                SELECT id
                FROM update_logs
                ORDER BY created_at DESC, id DESC
                LIMIT 200
            )
            """
        )
        connection.commit()


def get_latest_draw_metadata(lottery_type: str) -> dict[str, Any]:
    table_name = LOTTERY_TABLES[lottery_type]
    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT issue, draw_date, source_url, updated_at
            FROM {table_name}
            ORDER BY draw_date DESC, issue DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return {"issue": "-", "draw_date": "-", "source_url": None, "updated_at": None}
    return dict(row)


def get_latest_update_log(lottery_type: str) -> dict[str, Any]:
    return _get_latest_log(
        lottery_type=lottery_type,
        status_filter=("updated", "skipped", "error"),
        empty_message="还没有执行过数据更新。",
    )


def get_latest_update_log_by_source(lottery_type: str, trigger_source: str) -> dict[str, Any]:
    return _get_latest_log(
        lottery_type=lottery_type,
        status_filter=("updated", "skipped", "error"),
        trigger_source=trigger_source,
        empty_message="还没有执行过这类数据更新。",
    )


def _get_latest_log(
    *,
    lottery_type: str,
    status_filter: tuple[str, ...] | None,
    empty_message: str,
    trigger_source: str | None = None,
) -> dict[str, Any]:
    clauses = ["lottery_type = ?"]
    params: list[Any] = [lottery_type]

    if status_filter:
        placeholders = ",".join("?" for _ in status_filter)
        clauses.append(f"status IN ({placeholders})")
        params.extend(status_filter)
    if trigger_source:
        clauses.append("trigger_source = ?")
        params.append(trigger_source)

    where_sql = " AND ".join(clauses)
    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT lottery_type, issue, run_id, trigger_source, status, source_url, message, created_at
            FROM update_logs
            WHERE {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            params,
        ).fetchone()
    if row is None:
        return {
            "lottery_type": lottery_type,
            "issue": "-",
            "run_id": None,
            "trigger_source": trigger_source,
            "status": "not_run",
            "source_url": None,
            "message": empty_message,
            "created_at": None,
        }
    payload = dict(row)
    payload["issue"] = payload["issue"] or "-"
    return payload


def get_latest_backfill_log(lottery_type: str) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT lottery_type, issue, run_id, trigger_source, status, source_url, message, created_at
            FROM update_logs
            WHERE lottery_type = ?
              AND status LIKE 'backfill_%'
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (lottery_type,),
        ).fetchone()
    if row is None:
        return {
            "lottery_type": lottery_type,
            "issue": "-",
            "run_id": None,
            "trigger_source": None,
            "status": "not_run",
            "source_url": None,
            "message": "还没有执行过历史回填。",
            "created_at": None,
        }
    payload = dict(row)
    payload["issue"] = payload["issue"] or "-"
    return payload


def get_latest_ai_log(lottery_type: str) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT lottery_type, issue, run_id, trigger_source, status, source_url, message, created_at
            FROM update_logs
            WHERE lottery_type = ?
              AND status LIKE 'ai_%'
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (lottery_type,),
        ).fetchone()
    if row is None:
        return {
            "lottery_type": lottery_type,
            "issue": "-",
            "run_id": None,
            "trigger_source": None,
            "status": "not_run",
            "source_url": None,
            "message": "还没有执行过 AI 摘要生成。",
            "created_at": None,
        }
    payload = dict(row)
    payload["issue"] = payload["issue"] or "-"
    return payload


def load_recent_update_logs(limit: int = 10) -> pd.DataFrame:
    return _load_update_logs(limit=limit, status_filter=("updated", "skipped", "error"))


def load_recent_update_logs_by_source(trigger_source: str, limit: int = 10) -> pd.DataFrame:
    return _load_update_logs(limit=limit, status_filter=("updated", "skipped", "error"), trigger_source=trigger_source)


def _load_update_logs(
    *,
    limit: int,
    status_filter: tuple[str, ...] | None,
    trigger_source: str | None = None,
) -> pd.DataFrame:
    clauses: list[str] = []
    params: list[Any] = []

    if status_filter:
        placeholders = ",".join("?" for _ in status_filter)
        clauses.append(f"status IN ({placeholders})")
        params.extend(status_filter)
    if trigger_source:
        clauses.append("trigger_source = ?")
        params.append(trigger_source)

    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)

    with get_connection() as connection:
        dataframe = pd.read_sql_query(
            f"""
            SELECT lottery_type, issue, run_id, trigger_source, status, source_url, message, created_at
            FROM update_logs
            {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            connection,
            params=(*params, limit),
        )
    if not dataframe.empty:
        dataframe["issue"] = dataframe["issue"].fillna("-")
    return dataframe


def load_latest_update_run_logs(trigger_source: str) -> pd.DataFrame:
    with get_connection() as connection:
        latest_run = connection.execute(
            """
            SELECT run_id
            FROM update_logs
            WHERE trigger_source = ?
              AND status IN ('updated', 'skipped', 'error')
              AND run_id IS NOT NULL
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (trigger_source,),
        ).fetchone()

        if latest_run is None or not latest_run["run_id"]:
            return pd.DataFrame()

        dataframe = pd.read_sql_query(
            """
            SELECT lottery_type, issue, run_id, trigger_source, status, source_url, message, created_at
            FROM update_logs
            WHERE run_id = ?
              AND status IN ('updated', 'skipped', 'error')
            ORDER BY created_at DESC, id DESC
            """,
            connection,
            params=(latest_run["run_id"],),
        )
    if not dataframe.empty:
        dataframe["issue"] = dataframe["issue"].fillna("-")
    return dataframe


def load_recent_backfill_logs(limit: int = 20) -> pd.DataFrame:
    with get_connection() as connection:
        dataframe = pd.read_sql_query(
            """
            SELECT lottery_type, issue, status, source_url, message, created_at
            FROM update_logs
            WHERE status LIKE 'backfill_%'
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            connection,
            params=(limit,),
        )
    if not dataframe.empty:
        dataframe["issue"] = dataframe["issue"].fillna("-")
    return dataframe


def load_recent_admin_alerts(limit: int = 20) -> pd.DataFrame:
    with get_connection() as connection:
        dataframe = pd.read_sql_query(
            """
            SELECT lottery_type, issue, status, source_url, message, created_at
            FROM update_logs
            WHERE status IN ('error', 'backfill_partial', 'backfill_empty', 'ai_fallback')
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            connection,
            params=(limit,),
        )
    if not dataframe.empty:
        dataframe["issue"] = dataframe["issue"].fillna("-")
    return dataframe


def get_draw_coverage_stats(lottery_type: str) -> dict[str, Any]:
    table_name = LOTTERY_TABLES[lottery_type]
    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                MIN(draw_date) AS earliest_date,
                MAX(draw_date) AS latest_date,
                MIN(issue) AS earliest_issue,
                MAX(issue) AS latest_issue,
                MAX(updated_at) AS last_data_update
            FROM {table_name}
            """
        ).fetchone()
    if row is None:
        return {
            "total_rows": 0,
            "earliest_date": None,
            "latest_date": None,
            "earliest_issue": None,
            "latest_issue": None,
            "last_data_update": None,
        }
    return dict(row)


def get_ai_analysis_cache(cache_key: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                cache_key,
                lottery_type,
                analysis_scope,
                latest_issue,
                draw_count,
                summary_text,
                source_type,
                model_name,
                created_at,
                updated_at
            FROM ai_analysis_cache
            WHERE cache_key = ?
            LIMIT 1
            """,
            (cache_key,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def upsert_ai_analysis_cache(record: dict[str, Any]) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO ai_analysis_cache (
                cache_key,
                lottery_type,
                analysis_scope,
                latest_issue,
                draw_count,
                summary_text,
                source_type,
                model_name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(cache_key) DO UPDATE SET
                lottery_type = excluded.lottery_type,
                analysis_scope = excluded.analysis_scope,
                latest_issue = excluded.latest_issue,
                draw_count = excluded.draw_count,
                summary_text = excluded.summary_text,
                source_type = excluded.source_type,
                model_name = excluded.model_name,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                record["cache_key"],
                record["lottery_type"],
                record["analysis_scope"],
                record.get("latest_issue"),
                record["draw_count"],
                record["summary_text"],
                record["source_type"],
                record.get("model_name"),
            ),
        )
        connection.execute(
            """
            DELETE FROM ai_analysis_cache
            WHERE id NOT IN (
                SELECT id
                FROM ai_analysis_cache
                ORDER BY updated_at DESC, id DESC
                LIMIT 500
            )
            """
        )
        connection.commit()
