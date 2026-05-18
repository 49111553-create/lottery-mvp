from __future__ import annotations

import pandas as pd
import streamlit as st

from db.init_db import initialize_database
from db.repository import (
    get_draw_coverage_stats,
    get_latest_ai_log,
    get_latest_backfill_log,
    get_latest_update_log,
    get_latest_update_log_by_source,
    load_recent_admin_alerts,
    load_recent_backfill_logs,
)
from services.auth import enforce_admin_access
from services.backfill import backfill_history
from services.updater import update_latest_draws


st.set_page_config(page_title="历史回填进度", page_icon="📚", layout="wide")
enforce_admin_access("历史回填进度")
initialize_database()

def _render_progress_block(title: str, stats: dict, latest_log: dict, target_limit: int) -> None:
    st.subheader(title)
    total_rows = int(stats["total_rows"] or 0)
    progress_ratio = min(total_rows / target_limit, 1.0) if target_limit else 0.0
    st.progress(progress_ratio, text=f"累计入库 {total_rows} / 目标参考 {target_limit}")

    col1, col2 = st.columns(2)
    col1.metric("累计期数", total_rows)
    col2.metric("最近回填状态", _format_backfill_status(latest_log["status"]))

    col3, col4 = st.columns(2)
    col3.metric("最早期号", stats["earliest_issue"] or "-")
    col4.metric("最新期号", stats["latest_issue"] or "-")

    st.caption(
        f"数据覆盖：{stats['earliest_date'] or '-'} 至 {stats['latest_date'] or '-'} | "
        f"最近写库时间：{stats['last_data_update'] or '未更新'}"
    )
    st.info(f"最近回填说明：{latest_log['message']}")
    st.caption(f"最近回填执行时间：{latest_log['created_at'] or '未执行'}")


def _format_backfill_logs(dataframe: pd.DataFrame) -> pd.DataFrame:
    display = dataframe.copy()
    display["lottery_type"] = display["lottery_type"].map({"ssq": "双色球", "dlt": "大乐透"}).fillna(display["lottery_type"])
    display["status"] = display["status"].map(
        {
            "backfill_completed": "回填完成",
            "backfill_partial": "部分完成",
            "backfill_empty": "无结果",
        }
    ).fillna(display["status"])
    return display.rename(
        columns={
            "lottery_type": "彩种",
            "issue": "期号",
            "status": "状态",
            "message": "说明",
            "created_at": "执行时间",
            "source_url": "来源",
        }
    )


def _format_manual_backfill_results(dataframe: pd.DataFrame) -> pd.DataFrame:
    display = dataframe.copy()
    display["lottery_type"] = display["lottery_type"].map({"ssq": "双色球", "dlt": "大乐透"}).fillna(display["lottery_type"])
    display["status"] = display["status"].map(
        {
            "backfill_completed": "回填完成",
            "backfill_partial": "部分完成",
            "backfill_empty": "无结果",
        }
    ).fillna(display["status"])
    return display.rename(
        columns={
            "lottery_type": "彩种",
            "requested_limit": "请求上限",
            "processed": "已处理",
            "inserted": "新增",
            "updated": "覆盖更新",
            "errors": "失败",
            "status": "状态",
            "message": "说明",
        }
    )


def _format_backfill_status(status: str) -> str:
    mapping = {
        "backfill_completed": "回填完成",
        "backfill_partial": "部分完成",
        "backfill_empty": "无结果",
        "not_run": "未执行",
    }
    return mapping.get(status, status)


def _render_admin_alerts() -> None:
    st.subheader("后台告警")
    recent_alerts = load_recent_admin_alerts(limit=12)
    ssq_update_log = get_latest_update_log("ssq")
    dlt_update_log = get_latest_update_log("dlt")
    ssq_ai_log = get_latest_ai_log("ssq")
    dlt_ai_log = get_latest_ai_log("dlt")

    update_errors = int((recent_alerts["status"] == "error").sum()) if not recent_alerts.empty else 0
    backfill_alerts = int(recent_alerts["status"].isin(["backfill_partial", "backfill_empty"]).sum()) if not recent_alerts.empty else 0
    ai_alerts = int((recent_alerts["status"] == "ai_fallback").sum()) if not recent_alerts.empty else 0

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("最近告警数", len(recent_alerts))
    top2.metric("更新失败", update_errors)
    top3.metric("回填异常", backfill_alerts)
    top4.metric("AI 回退", ai_alerts)

    col1, col2 = st.columns(2, gap="large")
    with col1:
        _render_status_box("双色球最近更新", ssq_update_log, {"updated", "skipped"})
        _render_status_box("双色球最近 AI", ssq_ai_log, {"ai_generated", "ai_local"})
    with col2:
        _render_status_box("大乐透最近更新", dlt_update_log, {"updated", "skipped"})
        _render_status_box("大乐透最近 AI", dlt_ai_log, {"ai_generated", "ai_local"})

    if recent_alerts.empty:
        st.success("最近没有新的后台告警。")
    else:
        st.warning("最近有需要留意的后台信号，建议优先查看下面的告警列表。")
        st.dataframe(
            _format_alert_logs(recent_alerts),
            use_container_width=True,
            hide_index=True,
        )


def _render_latest_failure_reason() -> None:
    st.subheader("最近一次失败原因")
    recent_alerts = load_recent_admin_alerts(limit=20)

    if recent_alerts.empty:
        st.success("最近没有新的失败或回退记录。")
        return

    latest_alert = recent_alerts.iloc[0].to_dict()
    status_text = _format_admin_status(str(latest_alert["status"]))
    lottery_text = {"ssq": "双色球", "dlt": "大乐透"}.get(str(latest_alert["lottery_type"]), str(latest_alert["lottery_type"]))

    if str(latest_alert["status"]) == "error":
        st.error(f"{lottery_text}最近一次失败：{latest_alert['message']}")
    else:
        st.warning(f"{lottery_text}最近一次异常：{latest_alert['message']}")

    top1, top2, top3 = st.columns(3)
    top1.metric("彩种", lottery_text)
    top2.metric("状态", status_text)
    top3.metric("发生时间", latest_alert["created_at"] or "未记录")

    st.caption(f"期号：{latest_alert['issue'] or '-'}")
    if latest_alert.get("source_url"):
        st.caption(f"来源：{latest_alert['source_url']}")


def _render_status_box(title: str, log: dict, ok_statuses: set[str]) -> None:
    st.markdown(f"**{title}**")
    if log["status"] in ok_statuses:
        st.success(f"{_format_admin_status(log['status'])} | {log['message']}")
    elif log["status"] == "not_run":
        st.info(log["message"])
    else:
        st.error(f"{_format_admin_status(log['status'])} | {log['message']}")
    st.caption(f"期号：{log['issue']} | 时间：{log['created_at'] or '未执行'}")


def _format_alert_logs(dataframe: pd.DataFrame) -> pd.DataFrame:
    display = dataframe.copy()
    display["lottery_type"] = display["lottery_type"].map({"ssq": "双色球", "dlt": "大乐透"}).fillna(display["lottery_type"])
    display["status"] = display["status"].map(
        {
            "error": "更新失败",
            "backfill_partial": "回填部分完成",
            "backfill_empty": "回填无结果",
            "ai_fallback": "AI 回退本地摘要",
        }
    ).fillna(display["status"])
    return display.rename(
        columns={
            "lottery_type": "彩种",
            "issue": "期号",
            "status": "状态",
            "message": "说明",
            "created_at": "时间",
            "source_url": "来源",
        }
    )


def _format_admin_status(status: str) -> str:
    mapping = {
        "updated": "已更新",
        "skipped": "已存在",
        "error": "更新失败",
        "ai_generated": "AI 已生成",
        "ai_local": "本地摘要",
        "ai_fallback": "AI 回退",
        "backfill_partial": "回填部分完成",
        "backfill_empty": "回填无结果",
        "not_run": "未执行",
    }
    return mapping.get(status, status)


def _format_manual_update_results(dataframe: pd.DataFrame) -> pd.DataFrame:
    display = dataframe.copy()
    display["lottery_type"] = display["lottery_type"].map({"ssq": "双色球", "dlt": "大乐透"}).fillna(display["lottery_type"])
    display["status"] = display["status"].map(
        {
            "updated": "已更新",
            "skipped": "已存在，已跳过",
            "error": "更新失败",
        }
    ).fillna(display["status"])
    return display.rename(
        columns={
            "lottery_type": "彩种",
            "issue": "期号",
            "status": "状态",
            "message": "说明",
            "source_url": "来源",
        }
    )


def _render_manual_update_result_summary(results: list[dict]) -> None:
    result_frame = pd.DataFrame(results)
    updated_count = int((result_frame["status"] == "updated").sum())
    skipped_count = int((result_frame["status"] == "skipped").sum())
    error_count = int((result_frame["status"] == "error").sum())

    sub1, sub2, sub3 = st.columns(3)
    sub1.metric("本次新增更新", updated_count)
    sub2.metric("已存在跳过", skipped_count)
    sub3.metric("本次失败", error_count)

    if error_count:
        st.error(f"本次手动更新有 {error_count} 项失败，建议先看下方结果表里的失败原因。")
    elif updated_count:
        st.success(f"本次手动更新完成，新增写入 {updated_count} 项。")
    else:
        st.info("本次没有新增数据，当前最新期号已经在库中。")


def _render_manual_update_overview() -> None:
    st.subheader("最近一次手动更新时间总览")
    ssq_update_log = get_latest_update_log_by_source("ssq", "manual")
    dlt_update_log = get_latest_update_log_by_source("dlt", "manual")

    latest_time = max(
        [value for value in [ssq_update_log.get("created_at"), dlt_update_log.get("created_at")] if value],
        default="未执行",
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("最近更新时刻", latest_time)
    col2.metric("双色球状态", _format_admin_status(ssq_update_log["status"]))
    col3.metric("大乐透状态", _format_admin_status(dlt_update_log["status"]))

    detail_left, detail_right = st.columns(2, gap="large")
    with detail_left:
        st.markdown("**双色球最近更新**")
        st.caption(f"期号：{ssq_update_log['issue']} | 时间：{ssq_update_log['created_at'] or '未执行'}")
        st.write(ssq_update_log["message"])
    with detail_right:
        st.markdown("**大乐透最近更新**")
        st.caption(f"期号：{dlt_update_log['issue']} | 时间：{dlt_update_log['created_at'] or '未执行'}")
        st.write(dlt_update_log["message"])

    if st.session_state.get("last_update_results"):
        _render_manual_update_result_summary(st.session_state["last_update_results"])


st.title("历史回填进度")
st.caption("用于查看双色球和大乐透历史数据回填的累计进度、覆盖范围和最近一次回填结果。")

target_limit = st.sidebar.number_input("目标期数参考值", min_value=100, max_value=100000, value=10000, step=100)
st.sidebar.caption("这个数值只用于进度参考，不会直接触发回填。")

_render_admin_alerts()
st.divider()
_render_latest_failure_reason()
st.divider()
_render_manual_update_overview()
st.divider()

st.subheader("后台手动操作")
action_left, action_right = st.columns(2, gap="large")

with action_left:
    st.markdown("**最新开奖更新**")
    with st.form("manual_update_form"):
        update_confirmed = st.checkbox("我确认现在要手动触发最新开奖更新。")
        update_submitted = st.form_submit_button("更新最新数据", use_container_width=True)

    if update_submitted:
        if not update_confirmed:
            st.warning("请先勾选确认，再执行最新数据更新。")
        else:
            with st.spinner("正在抓取最新开奖数据..."):
                update_results = update_latest_draws(trigger_source="manual")
            st.session_state["last_update_results"] = update_results
            st.rerun()

    if st.session_state.get("last_update_results"):
        st.markdown("**最近一次手动更新结果**")
        st.dataframe(
            _format_manual_update_results(pd.DataFrame(st.session_state["last_update_results"])),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("适合在官方开奖页已经更新，但你不想等定时任务时手动执行。")

with action_right:
    st.markdown("**历史数据回填**")
    with st.form("manual_backfill_form"):
        selected_lottery = st.selectbox(
            "回填范围",
            options=[
                ("all", "全部彩种"),
                ("ssq", "只回填双色球"),
                ("dlt", "只回填大乐透"),
            ],
            format_func=lambda item: item[1],
        )
        selected_limit = st.number_input(
            "本次最大尝试期数",
            min_value=100,
            max_value=100000,
            value=1000,
            step=100,
        )
        confirmed = st.checkbox("我确认现在要执行历史回填，过程可能持续较久。")
        submitted = st.form_submit_button("开始回填", use_container_width=True)

    if submitted:
        if not confirmed:
            st.warning("请先勾选确认，再执行历史回填。")
        else:
            with st.spinner("正在执行历史回填，这一步可能需要一些时间..."):
                results = backfill_history(lottery_type=selected_lottery[0], limit=int(selected_limit))
            st.session_state["last_backfill_results"] = results
            st.rerun()

    st.info(
        "建议先跑 100 或 1000 期确认链路正常，再逐步放大。"
        " 如果官方站点访问受限，回填会写入失败或空结果日志。"
    )

if st.session_state.get("last_backfill_results"):
    st.success("最近一次手动回填已执行，结果如下。")
    st.dataframe(
        _format_manual_backfill_results(pd.DataFrame(st.session_state["last_backfill_results"])),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

ssq_stats = get_draw_coverage_stats("ssq")
dlt_stats = get_draw_coverage_stats("dlt")
ssq_log = get_latest_backfill_log("ssq")
dlt_log = get_latest_backfill_log("dlt")

left, right = st.columns(2, gap="large")

with left:
    _render_progress_block("双色球", ssq_stats, ssq_log, target_limit)

with right:
    _render_progress_block("大乐透", dlt_stats, dlt_log, target_limit)

st.divider()
st.subheader("最近回填记录")
backfill_logs = load_recent_backfill_logs(limit=20)
if backfill_logs.empty:
    st.info("还没有执行过历史回填。可以先运行 `python scripts/backfill_history.py --lottery all --limit 100` 做第一轮测试。")
else:
    st.dataframe(
        _format_backfill_logs(backfill_logs),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("建议先看最近一条日志的处理期数和失败期数，再决定是否继续放大到更高上限。")
