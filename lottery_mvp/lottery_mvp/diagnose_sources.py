from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.data_sources import DltOfficialSource, SsqOfficialSource, USER_AGENT


def main() -> int:
    parser = argparse.ArgumentParser(description="诊断双色球和大乐透官方抓取源可达性与解析结果。")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    diagnostics = build_diagnostics()
    json_path = args.output_dir / "source_diagnostics.json"
    md_path = args.output_dir / "source_diagnostics.md"

    json_path.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown(diagnostics) + "\n", encoding="utf-8")
    print(md_path.read_text(encoding="utf-8"))
    return 0


def build_diagnostics() -> dict:
    ssq = SsqOfficialSource()
    dlt = DltOfficialSource()

    return {
        "network_checks": [
            probe_url("双色球列表页", ssq.list_url, ["双色球", "开奖"]),
            probe_url("双色球官网首页", ssq.homepage_url, ["双色球", "开奖公告"]),
            probe_url("大乐透计算器页", "https://m.lottery.gov.cn/mltsz/jsq/index.html?tt_force_outside=1", ["查询期数", "开奖号码"]),
            probe_url("大乐透开奖页", "https://m.lottery.gov.cn/tcwm/dlt/", ["超级大乐透", "开奖时间"]),
            probe_url("大乐透历史页", "https://m.lottery.gov.cn/zst/dlt/?tt_force_outside=1", ["最近30期", "期号"]),
        ],
        "parser_checks": [
            probe_fetch_latest("双色球抓取器", ssq.fetch_latest_draw),
            probe_fetch_latest("大乐透抓取器", dlt.fetch_latest_draw),
        ],
    }


def probe_url(name: str, url: str, expected_markers: list[str]) -> dict:
    result = {
        "name": name,
        "url": url,
        "ok": False,
        "host": urlparse(url).netloc,
        "content_length": 0,
        "markers_found": [],
        "error": None,
    }
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="ignore")
            result["ok"] = True
            result["content_length"] = len(body)
            result["markers_found"] = [marker for marker in expected_markers if marker in body]
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
    return result


def probe_fetch_latest(name: str, fetcher) -> dict:
    result = {
        "name": name,
        "ok": False,
        "issue": None,
        "draw_date": None,
        "source_url": None,
        "error": None,
    }
    try:
        record = fetcher()
        result["ok"] = True
        result["issue"] = record.issue
        result["draw_date"] = record.draw_date
        result["source_url"] = record.source_url
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
    return result


def build_markdown(diagnostics: dict) -> str:
    lines = [
        "## 抓取源诊断",
        "",
        "### 网络探测",
        "",
        "| 检查项 | 域名 | 是否可访问 | 内容长度 | 关键字命中 | 错误 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for item in diagnostics["network_checks"]:
        lines.append(
            "| {name} | {host} | {ok} | {content_length} | {markers} | {error} |".format(
                name=item["name"],
                host=item["host"],
                ok="是" if item["ok"] else "否",
                content_length=item["content_length"],
                markers="、".join(item["markers_found"]) or "-",
                error=(item["error"] or "-").replace("|", "/").replace("\n", " "),
            )
        )

    lines.extend(
        [
            "",
            "### 抓取器探测",
            "",
            "| 检查项 | 是否成功 | 期号 | 开奖日期 | 来源 | 错误 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )

    for item in diagnostics["parser_checks"]:
        lines.append(
            "| {name} | {ok} | {issue} | {draw_date} | {source_url} | {error} |".format(
                name=item["name"],
                ok="是" if item["ok"] else "否",
                issue=item["issue"] or "-",
                draw_date=item["draw_date"] or "-",
                source_url=item["source_url"] or "-",
                error=(item["error"] or "-").replace("|", "/").replace("\n", " "),
            )
        )

    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
