from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from lxml import html


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class DataSourceError(RuntimeError):
    pass


@dataclass
class DrawRecord:
    lottery_type: str
    issue: str
    draw_date: str
    main_numbers: list[int]
    extra_numbers: list[int]
    sales_amount: float | None = None
    prize_pool: float | None = None
    source_url: str | None = None


class BaseOfficialSource:
    timeout = 20

    def fetch_latest_draw(self) -> DrawRecord:
        raise NotImplementedError

    def parse_draw_page(self, page_html: str, source_url: str | None = None) -> DrawRecord:
        raise NotImplementedError

    def _fetch_text(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="ignore")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise DataSourceError(f"请求失败: {url}") from exc

    @staticmethod
    def _parse_money(raw_text: str) -> float | None:
        match = re.search(r"([\d,]+(?:\.\d+)?)", raw_text)
        if not match:
            return None
        return float(match.group(1).replace(",", ""))

    @staticmethod
    def _clean_text(raw_text: str) -> str:
        return re.sub(r"\s+", " ", raw_text).strip()

    @staticmethod
    def _extract_image_number_candidates(container) -> list[int]:
        values: list[int] = []
        for element in container.xpath(".//img|.//*[@data-src]|.//*[@src]"):
            attrs = [
                element.get("alt", ""),
                element.get("title", ""),
                element.get("src", ""),
                element.get("data-src", ""),
                element.get("data-original", ""),
            ]
            for attr in attrs:
                for token in re.findall(r"(?<!\d)(\d{1,2})(?=\D*$|\.png|\.jpg|\.jpeg|/)", attr):
                    values.append(int(token))
        return values

    def _extract_section_text(self, page_html: str, start_marker: str, end_marker: str) -> str:
        start = page_html.find(start_marker)
        if start == -1:
            return page_html
        end = page_html.find(end_marker, start)
        if end == -1:
            end = len(page_html)
        return page_html[start:end]


class SsqOfficialSource(BaseOfficialSource):
    list_url = "https://www.cwl.gov.cn/ygkj/ssq/kjgg/"
    homepage_url = "https://www.cwl.gov.cn/"

    def fetch_latest_draw(self) -> DrawRecord:
        detail_url = self._find_latest_detail_url()
        page_html = self._fetch_text(detail_url)
        return self.parse_draw_page(page_html, detail_url)

    def parse_draw_page(self, page_html: str, source_url: str | None = None) -> DrawRecord:
        issue = self._extract_issue(page_html)
        draw_date = self._extract_date(page_html)
        main_numbers, extra_numbers = self._extract_numbers(page_html)
        sales_amount = self._extract_money_by_label(page_html, "本期销售金额")
        prize_pool = self._extract_money_by_label(page_html, "下期一等奖奖池累计金额")

        return DrawRecord(
            lottery_type="ssq",
            issue=issue,
            draw_date=draw_date,
            main_numbers=main_numbers,
            extra_numbers=extra_numbers,
            sales_amount=sales_amount,
            prize_pool=prize_pool,
            source_url=source_url,
        )

    def _find_latest_detail_url(self) -> str:
        prioritized_candidates: list[str] = []
        generic_candidates: list[str] = []

        for page_url in (self.list_url, self.homepage_url):
            try:
                page_html = self._fetch_text(page_url)
                tree = html.fromstring(page_html)
                for element in tree.xpath("//a[@href]"):
                    href = element.get("href", "")
                    if not href:
                        continue
                    full_url = urljoin(page_url, href)
                    if not self._is_article_url(full_url):
                        continue

                    combined = self._clean_text(" ".join(element.xpath(".//text()")))
                    if "双色球" in combined and "开奖公告" in combined:
                        prioritized_candidates.append(full_url)
                    else:
                        generic_candidates.append(full_url)

                for raw_match in re.findall(r'["\']([^"\']+/c/\d{4}/\d{2}/\d{2}/\d+\.shtml)["\']', page_html):
                    full_url = urljoin(page_url, raw_match)
                    if self._is_article_url(full_url):
                        generic_candidates.append(full_url)
            except DataSourceError:
                continue

        for detail_url in _unique_in_order(prioritized_candidates + generic_candidates):
            try:
                page_html = self._fetch_text(detail_url)
            except DataSourceError:
                continue
            if self._looks_like_ssq_notice(page_html):
                return detail_url
        raise DataSourceError("无法定位双色球最新开奖公告链接。")

    @staticmethod
    def _extract_issue(page_html: str) -> str:
        patterns = [
            r"中国福利彩票[“\"]?双色球[”\"]?第(\d{7,8})期开奖公告",
            r"双色球[“\"]?第(\d{7,8})期开奖公告",
            r"<title>[^<]*双色球[^<]*第(\d{7,8})期开奖公告",
        ]
        for pattern in patterns:
            match = re.search(pattern, page_html)
            if match:
                return match.group(1)
        raise DataSourceError("无法从双色球开奖公告中解析期号。")

    @staticmethod
    def _extract_date(page_html: str) -> str:
        patterns = [
            r"开奖日期[：:]\s*(\d{4}-\d{2}-\d{2})",
            r"开奖日期[：:]\s*(\d{4}/\d{2}/\d{2})",
            r"开奖日期[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)",
        ]
        for pattern in patterns:
            match = re.search(pattern, page_html)
            if match:
                return _normalize_date(match.group(1))
        raise DataSourceError("无法从双色球开奖公告中解析开奖日期。")

    def _extract_numbers(self, page_html: str) -> tuple[list[int], list[int]]:
        section = self._extract_section_text(page_html, "开奖号码", "中奖情况")
        section_tree = html.fromstring(f"<div>{section}</div>")
        text_tokens = [
            int(token)
            for token in re.findall(r"(?<!\d)(0?[1-9]|[12]\d|3[0-3])(?!\d)", self._clean_text(section_tree.text_content()))
        ]
        image_tokens = self._extract_image_number_candidates(section_tree)
        all_tokens = text_tokens + image_tokens

        candidates = self._pick_token_window(all_tokens, main_upper=33, extra_upper=16, main_count=6, extra_count=1)
        if candidates is None:
            raise DataSourceError("无法从双色球开奖公告中解析开奖号码。")
        main_numbers, extra_numbers = candidates
        return main_numbers, extra_numbers

    def _extract_money_by_label(self, page_html: str, label: str) -> float | None:
        pattern = rf"{label}[：:]\s*([\d,]+(?:\.\d+)?)"
        match = re.search(pattern, page_html)
        if not match:
            return None
        return float(match.group(1).replace(",", ""))

    @staticmethod
    def _is_article_url(url: str) -> bool:
        return bool(re.search(r"/c/\d{4}/\d{2}/\d{2}/\d+\.shtml$", url))

    @classmethod
    def _looks_like_ssq_notice(cls, page_html: str) -> bool:
        clean_text = cls._clean_text(page_html)
        return "双色球" in clean_text and "开奖公告" in clean_text and bool(re.search(r"第\d{7,8}期开奖公告", clean_text))

    @staticmethod
    def _pick_token_window(
        tokens: Iterable[int],
        *,
        main_upper: int,
        extra_upper: int,
        main_count: int,
        extra_count: int,
    ) -> tuple[list[int], list[int]] | None:
        items = list(tokens)
        window_size = main_count + extra_count
        for index in range(0, len(items) - window_size + 1):
            window = items[index:index + window_size]
            main_numbers = window[:main_count]
            extra_numbers = window[main_count:]
            if all(1 <= value <= main_upper for value in main_numbers) and all(1 <= value <= extra_upper for value in extra_numbers):
                if len(set(main_numbers)) == len(main_numbers) and len(set(extra_numbers)) == len(extra_numbers):
                    return main_numbers, extra_numbers
        return None


class DltOfficialSource(BaseOfficialSource):
    candidate_urls = [
        "https://m.lottery.gov.cn/mltsz/jsq/index.html?tt_force_outside=1",
        "https://m.lottery.gov.cn/tcwm/dlt/",
        "https://m.lottery.gov.cn/mltsz/jsq/index.html",
        "https://m.lottery.gov.cn/zst/dlt/?tt_force_outside=1",
    ]

    def fetch_latest_draw(self) -> DrawRecord:
        errors: list[str] = []
        for url in self.candidate_urls:
            try:
                page_html = self._fetch_text(url)
                try:
                    return self.parse_draw_page(page_html, url)
                except DataSourceError as exc:
                    issue_candidates = self.extract_issue_candidates(page_html)
                    if issue_candidates:
                        for issue in issue_candidates[:3]:
                            try:
                                return self.fetch_draw_by_issue(issue)
                            except DataSourceError:
                                continue
                    errors.append(f"{url}: {exc}")
            except DataSourceError as exc:
                errors.append(f"{url}: {exc}")

        raise DataSourceError("无法从官方大乐透页面解析最新开奖信息。 " + " | ".join(errors))

    def parse_draw_page(self, page_html: str, source_url: str | None = None) -> DrawRecord:
        issue = self._extract_issue(page_html)
        draw_date = self._extract_date(page_html)
        main_numbers, extra_numbers = self._extract_numbers(page_html)
        sales_amount = self._extract_money_by_labels(page_html, ["本期销售", "本期销售额", "销售总额"])
        prize_pool = self._extract_money_by_labels(page_html, ["本期开奖后奖池", "奖池累计", "奖池"])
        return DrawRecord(
            lottery_type="dlt",
            issue=issue,
            draw_date=draw_date,
            main_numbers=main_numbers,
            extra_numbers=extra_numbers,
            sales_amount=sales_amount,
            prize_pool=prize_pool,
            source_url=source_url,
        )

    def fetch_draw_by_issue(self, issue: str) -> DrawRecord:
        errors: list[str] = []
        for url in self._candidate_issue_urls(issue):
            try:
                page_html = self._fetch_text(url)
                record = self.parse_draw_page(page_html, url)
                if record.issue == issue:
                    return record
            except DataSourceError as exc:
                errors.append(f"{url}: {exc}")
        raise DataSourceError(f"无法按期号抓取大乐透 {issue}。 " + " | ".join(errors))

    def extract_issue_candidates(self, page_html: str) -> list[str]:
        patterns = [
            r'<option[^>]+value=["\']?(\d{5,8})["\']?',
            r'"issue"\s*:\s*"(\d{5,8})"',
            r'"period"\s*:\s*"(\d{5,8})"',
            r"第\s*(\d{5,8})\s*期",
        ]
        values: list[str] = []
        for pattern in patterns:
            values.extend(re.findall(pattern, page_html))
        return sorted({value for value in values if value.isdigit()}, key=int, reverse=True)

    @staticmethod
    def _candidate_issue_urls(issue: str) -> list[str]:
        return [
            f"https://m.lottery.gov.cn/mltsz/jsq/index.html?tt_force_outside=1&issue={issue}",
            f"https://m.lottery.gov.cn/mltsz/jsq/index.html?tt_force_outside=1&period={issue}",
            f"https://m.lottery.gov.cn/tcwm/dlt/?issue={issue}",
            f"https://m.lottery.gov.cn/tcwm/dlt/?period={issue}",
            f"https://m.lottery.gov.cn/zst/dlt/?tt_force_outside=1&issue={issue}",
            f"https://m.lottery.gov.cn/zst/dlt/?tt_force_outside=1&period={issue}",
        ]

    def _extract_issue(self, page_html: str) -> str:
        patterns = [
            r"第\s*(\d{5,8})\s*期",
            r'"issue"\s*:\s*"(\d{5,8})"',
            r'"period"\s*:\s*"(\d{5,8})"',
            r'<option[^>]*selected[^>]*value=["\']?(\d{5,8})["\']?',
        ]
        for pattern in patterns:
            match = re.search(pattern, page_html)
            if match:
                return match.group(1)
        issue_candidates = self.extract_issue_candidates(page_html)
        if issue_candidates:
            return issue_candidates[0]
        raise DataSourceError("无法解析大乐透期号。")

    @staticmethod
    def _extract_date(page_html: str) -> str:
        patterns = [
            r"(\d{4}-\d{2}-\d{2})",
            r"(\d{4}/\d{2}/\d{2})",
            r"(\d{4}年\d{1,2}月\d{1,2}日)",
        ]
        for pattern in patterns:
            match = re.search(pattern, page_html)
            if match:
                return _normalize_date(match.group(1))
        return date.today().isoformat()

    def _extract_numbers(self, page_html: str) -> tuple[list[int], list[int]]:
        section = self._extract_section_text(page_html, "开奖号码", "奖池")
        tokens = [
            int(token)
            for token in re.findall(r"(?<!\d)(0?[1-9]|[12]\d|3[0-5])(?!\d)", section)
        ]
        candidates = SsqOfficialSource._pick_token_window(tokens, main_upper=35, extra_upper=12, main_count=5, extra_count=2)
        if candidates is not None:
            return candidates

        tree = html.fromstring(page_html)
        image_tokens = self._extract_image_number_candidates(tree)
        candidates = SsqOfficialSource._pick_token_window(image_tokens, main_upper=35, extra_upper=12, main_count=5, extra_count=2)
        if candidates is None:
            raise DataSourceError("无法解析大乐透开奖号码。")
        return candidates

    def _extract_money_by_labels(self, page_html: str, labels: list[str]) -> float | None:
        for label in labels:
            pattern = rf"{label}[：:\s]*([\d,]+(?:\.\d+)?)"
            match = re.search(pattern, page_html)
            if match:
                return float(match.group(1).replace(",", ""))
        return None


def _normalize_date(raw_value: str) -> str:
    if "-" in raw_value:
        return raw_value
    if "/" in raw_value:
        return raw_value.replace("/", "-")
    match = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", raw_value)
    if not match:
        raise DataSourceError(f"无法标准化日期: {raw_value}")
    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def _unique_in_order(values: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered
