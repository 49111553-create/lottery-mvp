import json

import pandas as pd

from config import LOTTERY_CONFIG
from data_service import dataframe_to_json, frequency_stats, omission_stats, parse_numbers, simulate_numbers
from db import get_stats_cache, save_stats_cache


def _cache_key(lottery_type: str, stat_type: str, period: int):
    return f"{lottery_type}:{stat_type}:{period}"


def _frame_from_cache(cache_key: str):
    cached = get_stats_cache(cache_key)
    if not cached:
        return None
    rows = json.loads(cached["cache_json"])
    return pd.DataFrame(rows)


def _save_frame_cache(lottery_type: str, stat_type: str, period: int, df: pd.DataFrame):
    save_stats_cache(
        lottery_type,
        stat_type,
        str(period),
        _cache_key(lottery_type, stat_type, period),
        dataframe_to_json(df),
    )


def get_frequency_stats(df: pd.DataFrame, lottery_type: str, period: int):
    key = _cache_key(lottery_type, "frequency", period)
    cached = _frame_from_cache(key)
    if cached is not None and not cached.empty:
        return cached
    result = frequency_stats(df.head(period))
    _save_frame_cache(lottery_type, "frequency", period, result)
    return result


def get_omission_stats(df: pd.DataFrame, lottery_type: str, period: int):
    key = _cache_key(lottery_type, "omission", period)
    cached = _frame_from_cache(key)
    if cached is not None and not cached.empty:
        return cached
    result = omission_stats(df.head(period), lottery_type)
    _save_frame_cache(lottery_type, "omission", period, result)
    return result


def calc_odd_even_stats(df: pd.DataFrame):
    odd = 0
    even = 0
    for text in df["numbers_main"].tolist():
        for n in parse_numbers(text):
            if n % 2:
                odd += 1
            else:
                even += 1
    return {"odd": odd, "even": even}


def calc_zone_stats(df: pd.DataFrame, lottery_type: str):
    cfg = LOTTERY_CONFIG[lottery_type]
    top = cfg["main_max"]
    step = max((top - cfg["main_min"] + 1) // 3, 1)
    zones = {"一区": 0, "二区": 0, "三区": 0}
    for text in df["numbers_main"].tolist():
        for n in parse_numbers(text):
            if n < cfg["main_min"] + step:
                zones["一区"] += 1
            elif n < cfg["main_min"] + step * 2:
                zones["二区"] += 1
            else:
                zones["三区"] += 1
    return zones


def calc_sum_stats(df: pd.DataFrame):
    values = [sum(parse_numbers(text)) for text in df["numbers_main"].tolist()]
    if not values:
        return {"avg": 0, "max": 0, "min": 0}
    return {"avg": round(sum(values) / len(values), 1), "max": max(values), "min": min(values)}


def build_number_plan(lottery_type: str, mode: str):
    main, extra = simulate_numbers(lottery_type, mode)
    reason = {
        "随机生成": "用于快速给出一组不带偏见的娱乐性组合。",
        "冷热均衡": "在号码结构上做轻度平衡，更适合展示冷热搭配思路。",
        "区间均衡": "让号码尽量覆盖不同区间，减少过于集中的组合。",
    }.get(mode, "用于娱乐参考。")
    return {"main": main, "extra": extra, "reason": reason}
