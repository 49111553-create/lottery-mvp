from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.updater import update_latest_draws


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取并写入最新双色球和大乐透开奖数据。")
    parser.add_argument("--summary-file", type=Path, default=None, help="把本次更新结果写入指定 JSON 文件。")
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="只要本次有任一彩种更新失败，就返回非 0 状态码，适合自动化任务使用。",
    )
    args = parser.parse_args()

    results = update_latest_draws(trigger_source="auto")
    payload = json.dumps(results, ensure_ascii=False, indent=2)
    print(payload)

    if args.summary_file is not None:
        args.summary_file.parent.mkdir(parents=True, exist_ok=True)
        args.summary_file.write_text(payload + "\n", encoding="utf-8")

    if args.fail_on_error and any(item.get("status") == "error" for item in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
