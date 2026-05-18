import json
import re
from datetime import datetime
from html import unescape
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from config import HTTP_TIMEOUT, LOTTERY_CONFIG, OFFICIAL_SOURCE_URLS, SOURCE_USER_AGENT


class SourceFetchError(RuntimeError):
    pass


def _fetch_html(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": SOURCE_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.google.com/",
        },
    )
    with urlopen(req, timeout=HTTP_TIMEOUT) as response:
        return response.read().decode("utf-8", "ignore")


def _strip_tags(html: str) -> str:
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _extract_article_url(index_html: str, base_url: str, lottery_name: str) -> str:
    patterns = [
        rf'href="(?P<url>/c/\d{{4}}/\d{{2}}/\d{{2}}/\d+\.shtml)".*?{re.escape(lottery_name)}.*?开奖公告',
        rf'(?P<url>/c/\d{{4}}/\d{{2}}/\d{{2}}/\d+\.shtml).*?{re.escape(lottery_name)}.*?开奖公告',
    ]
    for pattern in patterns:
        match = re.search(pattern, index_html, flags=re.I | re.S)
        if match:
            return urljoin(base_url, match.group("url"))
    raise SourceFetchError(f"未在列表页中找到 {lottery_name} 最新开奖公告")


def _extract_issue(text: str, lottery_name: str) -> str:
    patterns = [
        rf"{re.escape(lottery_name)}[”\"]?第(\d+)期",
        r"第(\d+)期开奖公告",
        r"第(\d+)期",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    raise SourceFetchError("未识别到期号")


def _extract_draw_date(text: str) -> str:
    match = re.search(r"开奖日期[:：]\s*(\d{4}-\d{2}-\d{2})", text)
    if match:
        return match.group(1)
    raise SourceFetchError("未识别到开奖日期")


def _extract_money(text: str, labels: list[str]) -> float:
    for label in labels:
        match = re.search(rf"{label}[:：]?\s*([0-9,]+(?:\.\d+)?)\s*元", text)
        if match:
            return float(match.group(1).replace(",", ""))
    return 0.0


def _extract_candidate_sequences(text: str):
    candidates = []
    for match in re.finditer(r"(?:\d{1,2}[,\s、\-|]){2,24}\d{1,2}", text):
        raw = match.group(0)
        nums = re.findall(r"\d{1,2}", raw)
        if nums:
            candidates.append(nums)
    for match in re.finditer(r"开奖号码[:：]?\s*([0-9]{3,20})", text):
        raw = match.group(1)
        candidates.append(list(raw))
    return candidates


def _extract_from_json_blob(html: str, total_count: int):
    patterns = [
        r'"preDrawCode"\s*:\s*"([^"]+)"',
        r'"kjhm"\s*:\s*"([^"]+)"',
        r'"openCode"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            nums = re.findall(r"\d{1,2}", match.group(1))
            if len(nums) >= total_count:
                return nums[:total_count]
    return []


def _extract_numbers(html: str, lottery_type: str):
    cfg = LOTTERY_CONFIG[lottery_type]
    total_count = cfg["main_count"] + cfg["extra_count"]
    nums = _extract_from_json_blob(html, total_count)
    if not nums:
        text = _strip_tags(html)
        for candidate in _extract_candidate_sequences(text):
            if len(candidate) == total_count:
                nums = candidate
                break
            if lottery_type in {"fc3d", "pl3", "pl5"} and len(candidate) >= cfg["main_count"]:
                nums = candidate[: cfg["main_count"]]
                break
    if not nums:
        raise SourceFetchError("未识别到开奖号码")
    main = nums[: cfg["main_count"]]
    extra = nums[cfg["main_count"] : cfg["main_count"] + cfg["extra_count"]]
    return ",".join(main), ",".join(extra)


def _fetch_cwl_latest(lottery_type: str):
    lottery_name = LOTTERY_CONFIG[lottery_type]["name"]
    index_url = OFFICIAL_SOURCE_URLS[lottery_type]
    index_html = _fetch_html(index_url)
    article_url = _extract_article_url(index_html, index_url, lottery_name)
    html = _fetch_html(article_url)
    text = _strip_tags(html)
    issue = _extract_issue(text, lottery_name)
    draw_date = _extract_draw_date(text)
    numbers_main, numbers_extra = _extract_numbers(html, lottery_type)
    sales = _extract_money(text, ["本期销售金额"])
    jackpot = _extract_money(text, ["下期一等奖奖池累计金额", "奖池累计金额", "“选十”玩法奖池累计金额"])
    return {
        "lottery_type": lottery_type,
        "issue": issue,
        "draw_date": draw_date,
        "numbers_main": numbers_main,
        "numbers_extra": numbers_extra,
        "sales_amount": sales,
        "jackpot_amount": jackpot,
        "source_name": "official_cwl",
        "source_url": article_url,
        "ingested_at": datetime.utcnow().isoformat(),
    }


def _fetch_lottery_gov_latest(lottery_type: str):
    url = OFFICIAL_SOURCE_URLS[lottery_type]
    html = _fetch_html(url)
    text = _strip_tags(html)
    lottery_name = LOTTERY_CONFIG[lottery_type]["name"]
    issue = _extract_issue(text, lottery_name)
    draw_date = _extract_draw_date(text)
    numbers_main, numbers_extra = _extract_numbers(html, lottery_type)
    sales = _extract_money(text, ["本期销售", "本期销售金额"])
    jackpot = _extract_money(text, ["奖池累计", "本期开奖后奖池"])
    return {
        "lottery_type": lottery_type,
        "issue": issue,
        "draw_date": draw_date,
        "numbers_main": numbers_main,
        "numbers_extra": numbers_extra,
        "sales_amount": sales,
        "jackpot_amount": jackpot,
        "source_name": "official_lottery_gov",
        "source_url": url,
        "ingested_at": datetime.utcnow().isoformat(),
    }


def fetch_latest_official_draw(lottery_type: str):
    if lottery_type in {"ssq", "fc3d", "qlc", "kl8"}:
        return _fetch_cwl_latest(lottery_type)
    if lottery_type in {"dlt", "pl3", "pl5"}:
        return _fetch_lottery_gov_latest(lottery_type)
    raise SourceFetchError(f"暂不支持的彩种: {lottery_type}")
