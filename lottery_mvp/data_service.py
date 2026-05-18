import io
import random
from datetime import date, datetime, timedelta

import pandas as pd

from config import ALLOW_DEMO_FALLBACK, LOTTERY_CONFIG
from db import log_update, select_draws, upsert_draws
from source_fetchers import fetch_latest_official_draw


def parse_numbers(text: str):
    if not text:
        return []
    return [int(x) for x in text.split(",") if x != ""]


def format_numbers(nums):
    return ",".join(f"{n:02d}" if n > 9 else str(n) for n in nums)


def _sample_issue(lottery_type: str, offset: int) -> str:
    year = date.today().year
    return f"{year}{offset:03d}"


def random_draw(lottery_type: str, offset: int):
    cfg = LOTTERY_CONFIG[lottery_type]
    main_pool = list(range(cfg["main_min"], cfg["main_max"] + 1))
    if cfg["main_min"] == 0:
        main = [random.choice(main_pool) for _ in range(cfg["main_count"])]
    else:
        main = sorted(random.sample(main_pool, cfg["main_count"]))
    extra = []
    if cfg["extra_count"]:
        extra_pool = list(range(cfg["extra_min"], cfg["extra_max"] + 1))
        if cfg["extra_min"] == 0:
            extra = [random.choice(extra_pool) for _ in range(cfg["extra_count"])]
        else:
            extra = sorted(random.sample(extra_pool, cfg["extra_count"]))
    draw_day = date.today() - timedelta(days=offset)
    return {
        "lottery_type": lottery_type,
        "issue": _sample_issue(lottery_type, 300 - offset),
        "draw_date": draw_day.isoformat(),
        "numbers_main": format_numbers(main),
        "numbers_extra": format_numbers(extra),
        "sales_amount": random.randint(1_000_000, 50_000_000),
        "jackpot_amount": random.randint(500_000, 20_000_000),
        "source_name": "demo_seed",
        "source_url": "",
        "ingested_at": datetime.utcnow().isoformat(),
    }


def seed_demo_data(days: int = 60):
    rows = []
    for lottery_type in LOTTERY_CONFIG:
        for offset in range(days):
            rows.append(random_draw(lottery_type, offset))
    count = upsert_draws(rows)
    log_update("seed_demo_data", "success", f"upserted={count}")
    return count


def run_daily_update():
    rows = []
    details = []
    for lottery_type in LOTTERY_CONFIG:
        try:
            row = fetch_latest_official_draw(lottery_type)
            details.append(f"{lottery_type}:official:{row['issue']}")
        except Exception as exc:
            if not ALLOW_DEMO_FALLBACK:
                log_update("daily_update", "failed", f"{lottery_type}: {exc}")
                raise
            row = random_draw(lottery_type, 0)
            row["source_name"] = "demo_fallback"
            row["source_url"] = ""
            details.append(f"{lottery_type}:fallback:{exc}")
        rows.append(row)
    count = upsert_draws(rows)
    log_update("daily_update", "success", f"upserted={count}; " + " | ".join(details))
    return count


def load_draws(lottery_type: str, limit: int = 100):
    return pd.DataFrame(select_draws(lottery_type, limit))


def export_csv(df: pd.DataFrame):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8-sig")


def frequency_stats(df: pd.DataFrame):
    all_nums = []
    for value in df["numbers_main"].tolist():
        all_nums.extend(parse_numbers(value))
    if not all_nums:
        return pd.DataFrame(columns=["number", "count"])
    stats = pd.Series(all_nums).value_counts().sort_index().reset_index()
    stats.columns = ["number", "count"]
    return stats


def omission_stats(df: pd.DataFrame, lottery_type: str):
    cfg = LOTTERY_CONFIG[lottery_type]
    numbers = list(range(cfg["main_min"], cfg["main_max"] + 1))
    current = {n: 0 for n in numbers}
    max_gap = {n: 0 for n in numbers}
    seen = {n: False for n in numbers}
    for _, row in df.sort_values("draw_date", ascending=False).iterrows():
        draw_nums = set(parse_numbers(row["numbers_main"]))
        for n in numbers:
            if n in draw_nums:
                seen[n] = True
                current[n] = 0
            else:
                current[n] += 1
                max_gap[n] = max(max_gap[n], current[n])
    return pd.DataFrame(
        {
            "number": numbers,
            "current_omission": [current[n] for n in numbers],
            "max_omission": [max_gap[n] for n in numbers],
            "seen": [seen[n] for n in numbers],
        }
    )


def simulate_numbers(lottery_type: str, mode: str):
    cfg = LOTTERY_CONFIG[lottery_type]
    main_pool = list(range(cfg["main_min"], cfg["main_max"] + 1))
    if mode == "冷热均衡" and cfg["main_min"] != 0:
        middle = sorted(random.sample(main_pool, cfg["main_count"] - 1))
        main = sorted(middle + [random.choice(main_pool)])
    elif cfg["main_min"] == 0:
        main = [random.choice(main_pool) for _ in range(cfg["main_count"])]
    else:
        main = sorted(random.sample(main_pool, cfg["main_count"]))
    extra = []
    if cfg["extra_count"]:
        extra_pool = list(range(cfg["extra_min"], cfg["extra_max"] + 1))
        extra = sorted(random.sample(extra_pool, cfg["extra_count"]))
    return format_numbers(main), format_numbers(extra)


def build_ai_summary(df: pd.DataFrame, lottery_name: str):
    if df.empty:
        return f"{lottery_name} 暂无数据，建议先执行一次数据初始化或导入历史开奖。"
    latest = df.iloc[0]
    stats = frequency_stats(df.head(30))
    hot = "、".join(str(int(v)) for v in stats.sort_values("count", ascending=False).head(5)["number"])
    return (
        f"{lottery_name} 近 30 期里，活跃号码主要集中在 {hot}。"
        f" 最新一期为 {latest['issue']}，主号结构可作为区间分布与奇偶比观察样本。"
        " 这类结论仅用于统计观察和娱乐参考，不构成确定性预测。"
    )
