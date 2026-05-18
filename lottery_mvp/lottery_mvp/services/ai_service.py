import json

from db import get_ai_usage_count, get_stats_cache, log_ai_usage, save_stats_cache
from services.access_service import can_use_ai_feature, current_access_code
from services.stats_service import calc_odd_even_stats, calc_sum_stats, calc_zone_stats, get_frequency_stats


def get_usage_status():
    actor_key = current_access_code() or "guest"
    used = get_ai_usage_count(actor_key)
    allowed, limit = can_use_ai_feature(used)
    return actor_key, used, limit, allowed


def _cache_key(lottery_type: str, summary_type: str):
    return f"{lottery_type}:ai:{summary_type}"


def _load_cached_summary(lottery_type: str, summary_type: str):
    cached = get_stats_cache(_cache_key(lottery_type, summary_type))
    if not cached:
        return None
    payload = json.loads(cached["cache_json"])
    return payload.get("summary")


def _save_summary(lottery_type: str, summary_type: str, summary: str):
    save_stats_cache(
        lottery_type,
        "ai_summary",
        summary_type,
        _cache_key(lottery_type, summary_type),
        json.dumps({"summary": summary}, ensure_ascii=False),
    )


def build_daily_summary(lottery_type: str, lottery_name: str, df):
    cached = _load_cached_summary(lottery_type, "daily")
    if cached:
        return cached
    freq = get_frequency_stats(df, lottery_type, min(len(df), 30))
    hot = "、".join(str(int(v)) for v in freq.sort_values("count", ascending=False).head(5)["number"]) if not freq.empty else "暂无"
    odd_even = calc_odd_even_stats(df.head(30))
    zones = calc_zone_stats(df.head(30), lottery_type)
    summary = (
        f"{lottery_name} 今日观察：近 30 期活跃号码偏向 {hot}。"
        f" 奇偶分布约为 {odd_even['odd']}:{odd_even['even']}，"
        f"三区分布为 {zones['一区']}/{zones['二区']}/{zones['三区']}。"
        " 这是一段统计观察，不构成确定性预测。"
    )
    _save_summary(lottery_type, "daily", summary)
    return summary


def build_recent_trend_summary(lottery_type: str, lottery_name: str, df, period: int = 30):
    sums = calc_sum_stats(df.head(period))
    summary = (
        f"{lottery_name} 近 {period} 期和值均值约为 {sums['avg']}，"
        f"区间跨度在 {sums['min']} 到 {sums['max']} 之间。"
        " 更适合用于观察号码结构是否偏向集中或分散。"
    )
    return summary


def build_number_comment(lottery_name: str, numbers_main: str, numbers_extra: str):
    main_nums = [int(x) for x in numbers_main.split(",") if x]
    odd = len([n for n in main_nums if n % 2])
    even = len(main_nums) - odd
    spread = max(main_nums) - min(main_nums) if main_nums else 0
    tail = f"，附加号 {numbers_extra}" if numbers_extra else ""
    return (
        f"{lottery_name} 这组号码主号为 {numbers_main}{tail}。"
        f" 主号奇偶比 {odd}:{even}，跨度约 {spread}，"
        "更像一组结构平衡的娱乐性组合。"
    )


def consume_ai_usage(lottery_type: str, prompt_type: str):
    actor_key, used, limit, allowed = get_usage_status()
    if not allowed:
        return False, used, limit
    log_ai_usage(actor_key, current_access_code(), lottery_type, prompt_type)
    return True, used + 1, limit
