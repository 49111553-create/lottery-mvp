from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from db.init_db import initialize_database
from db.repository import create_update_log, get_latest_issue, upsert_dlt_draw, upsert_ssq_draw
from services.data_sources import DataSourceError, DltOfficialSource, DrawRecord, SsqOfficialSource


def update_latest_draws(trigger_source: str = "manual") -> list[dict[str, str | bool]]:
    initialize_database()
    sources = [SsqOfficialSource(), DltOfficialSource()]
    results: list[dict[str, str | bool]] = []
    run_id = _build_update_run_id(trigger_source)

    for source in sources:
        try:
            record = source.fetch_latest_draw()
            is_new = save_draw_record(record)
            status = "updated" if is_new else "skipped"
            message = "已写入最新开奖数据。" if is_new else "当前期号已存在，未重复写入。"
            create_update_log(
                lottery_type=record.lottery_type,
                issue=record.issue,
                status=status,
                source_url=record.source_url,
                message=message,
                run_id=run_id,
                trigger_source=trigger_source,
            )
            results.append(
                {
                    "lottery_type": record.lottery_type,
                    "issue": record.issue,
                    "status": status,
                    "source_url": record.source_url or "",
                    "message": message,
                }
            )
        except DataSourceError as exc:
            lottery_type = _resolve_lottery_type(source)
            create_update_log(
                lottery_type=lottery_type,
                issue=None,
                status="error",
                source_url=None,
                message=str(exc),
                run_id=run_id,
                trigger_source=trigger_source,
            )
            results.append(
                {
                    "lottery_type": lottery_type,
                    "issue": "-",
                    "status": "error",
                    "source_url": "",
                    "message": str(exc),
                }
            )

    return results


def _build_update_run_id(trigger_source: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{trigger_source}-{timestamp}-{uuid4().hex[:8]}"


def save_draw_record(record: DrawRecord) -> bool:
    latest_issue = get_latest_issue(record.lottery_type)
    payload = asdict(record)

    if record.lottery_type == "ssq":
        upsert_ssq_draw(
            {
                "issue": payload["issue"],
                "draw_date": payload["draw_date"],
                "red_numbers": ",".join(f"{value:02d}" for value in payload["main_numbers"]),
                "blue_number": payload["extra_numbers"][0],
                "sales_amount": payload["sales_amount"],
                "prize_pool": payload["prize_pool"],
                "source_url": payload["source_url"],
            }
        )
    else:
        upsert_dlt_draw(
            {
                "issue": payload["issue"],
                "draw_date": payload["draw_date"],
                "front_numbers": ",".join(f"{value:02d}" for value in payload["main_numbers"]),
                "back_numbers": ",".join(f"{value:02d}" for value in payload["extra_numbers"]),
                "sales_amount": payload["sales_amount"],
                "prize_pool": payload["prize_pool"],
                "source_url": payload["source_url"],
            }
        )

    return latest_issue != record.issue


def _resolve_lottery_type(source: object) -> str:
    if isinstance(source, SsqOfficialSource):
        return "ssq"
    if isinstance(source, DltOfficialSource):
        return "dlt"
    return "unknown"
