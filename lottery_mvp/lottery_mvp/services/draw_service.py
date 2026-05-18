from datetime import date

import pandas as pd

from config import LOTTERY_CONFIG
from data_service import export_csv, load_draws, parse_numbers, seed_demo_data
from db import get_latest_for_all_lotteries, query_draws


def get_home_cards():
    latest = get_latest_for_all_lotteries()
    cards = []
    for lottery_type, cfg in LOTTERY_CONFIG.items():
        row = latest.get(lottery_type)
        cards.append(
            {
                "lottery_type": lottery_type,
                "name": cfg["name"],
                "issue": row["issue"] if row else "-",
                "draw_date": row["draw_date"] if row else "-",
                "numbers_main": row["numbers_main"] if row else "",
                "numbers_extra": row["numbers_extra"] if row else "",
            }
        )
    return cards


def get_latest_draws(lottery_type: str, n: int = 5):
    return load_draws(lottery_type, limit=n)


def get_filtered_draws(
    lottery_type: str,
    issue_keyword: str = "",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
):
    return pd.DataFrame(
        query_draws(
            lottery_type,
            limit=limit,
            issue_keyword=issue_keyword,
            start_date=start_date,
            end_date=end_date,
        )
    )


def get_display_limit(is_member: bool):
    return 120 if is_member else 10


def latest_refresh_text():
    return date.today().isoformat()


def export_draws_csv(df: pd.DataFrame):
    return export_csv(df)


def seed_all_demo_data():
    return seed_demo_data()
