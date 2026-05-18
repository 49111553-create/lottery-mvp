from __future__ import annotations
import streamlit as st

from db.init_db import initialize_database
from db.repository import (
    get_latest_draw_metadata,
    get_latest_update_log,
    load_latest_update_run_logs,
    load_recent_draws,
    load_recent_update_logs,
)
from services.analytics import build_overview_metrics
from services.auth import enforce_access


def _format_status_text(status: str) -> str:
    mapping = {
        "updated": "已更新",
        "skipped": "已存在",
        "error": "更新失败",
        "not_run": "未执行",
    }
    return mapping.get(status, status)


def _render_home_update_overview() -> None:
    ssq_log = get_latest_update_log("ssq")
    dlt_log = get_latest_update_log("dlt")
    latest_time = max(
        [value for value in [ssq_log.get("created_at"), dlt_log.get("created_at")] if value],
        default="未执行",
    )

    st.subheader("最近一次更新时间总览")
    top1, top2, top3 = st.columns(3)
    top1.metric("最近更新时刻", latest_time)
    top2.metric("双色球状态", _format_status_text(ssq_log["status"]))
    top3.metric("大乐透状态", _format_status_text(dlt_log["status"]))

    detail_left, detail_right = st.columns(2, gap="large")
    with detail_left:
        st.markdown("**双色球最近更新**")
        st.caption(f"期号：{ssq_log['issue']} | 时间：{ssq_log['created_at'] or '未执行'}")
        st.write(ssq_log["message"])
    with detail_right:
        st.markdown("**大乐透最近更新**")
        st.caption(f"期号：{dlt_log['issue']} | 时间：{dlt_log['created_at'] or '未执行'}")
        st.write(dlt_log["message"])


def _format_home_update_logs(dataframe) -> object:
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
            "created_at": "执行时间",
        }
    )


def _render_latest_auto_update_section() -> None:
    auto_logs = load_latest_update_run_logs("auto")
    st.subheader("最近一次自动更新结果")
    st.caption("这部分结果来自 GitHub Actions 定时任务或手动触发的自动更新流程。")

    if auto_logs.empty:
        st.info("当前还没有自动更新记录。等定时任务或手动触发的自动更新跑完后，这里会自动显示。")
        return

    latest_time = auto_logs["created_at"].dropna().max() if "created_at" in auto_logs else None
    updated_count = int((auto_logs["status"] == "updated").sum())
    skipped_count = int((auto_logs["status"] == "skipped").sum())
    error_count = int((auto_logs["status"] == "error").sum())

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("执行时间", latest_time or "未记录")
    top2.metric("新增写入", updated_count)
    top3.metric("已存在跳过", skipped_count)
    top4.metric("更新失败", error_count)

    if error_count:
        st.error(f"最近一次自动更新有 {error_count} 项失败，建议去后台页查看失败原因。")
    elif updated_count:
        st.success(f"最近一次自动更新完成，新增写入 {updated_count} 项。")
    else:
        st.info("最近一次自动更新没有新增数据，当前最新期号已经在库中。")

    st.dataframe(
        _format_home_update_logs(auto_logs),
        use_container_width=True,
        hide_index=True,
    )


st.set_page_config(
    page_title="彩票数据分析助手",
    page_icon="📊",
    layout="wide",
)

enforce_access("彩票数据分析助手")
initialize_database()

st.title("彩票数据分析助手")
st.caption("用于历史数据查询、统计观察、娱乐性模拟选号和 AI 文案展示的 Streamlit MVP 骨架。")

_render_home_update_overview()
st.divider()
_render_latest_auto_update_section()
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("双色球")
    ssq_df = load_recent_draws("ssq", limit=20)
    ssq_metrics = build_overview_metrics(ssq_df, "ssq")
    ssq_meta = get_latest_draw_metadata("ssq")
    ssq_log = get_latest_update_log("ssq")
    st.metric("已载入期数", ssq_metrics["draw_count"])
    st.metric("最近期号", ssq_metrics["latest_issue"])
    st.metric("最近红球和值", ssq_metrics["latest_sum"])
    st.caption(
        f"开奖日期：{ssq_meta['draw_date']} | 数据更新时间：{ssq_meta['updated_at'] or '未更新'} | "
        f"最近状态：{_format_status_text(ssq_log['status'])}"
    )

with col2:
    st.subheader("大乐透")
    dlt_df = load_recent_draws("dlt", limit=20)
    dlt_metrics = build_overview_metrics(dlt_df, "dlt")
    dlt_meta = get_latest_draw_metadata("dlt")
    dlt_log = get_latest_update_log("dlt")
    st.metric("已载入期数", dlt_metrics["draw_count"])
    st.metric("最近期号", dlt_metrics["latest_issue"])
    st.metric("最近前区和值", dlt_metrics["latest_sum"])
    st.caption(
        f"开奖日期：{dlt_meta['draw_date']} | 数据更新时间：{dlt_meta['updated_at'] or '未更新'} | "
        f"最近状态：{_format_status_text(dlt_log['status'])}"
    )

st.divider()

left, right = st.columns([1.1, 0.9], gap="large")

with left:
    st.subheader("当前版本包含")
    st.markdown(
        """
        - 双色球分析页
        - 大乐透分析页
        - 历史开奖数据查询
        - 热门号与冷门号基础统计
        - 娱乐性模拟号码生成
        - AI 分析摘要占位区
        """
    )

    st.subheader("推荐下一步")
    st.markdown(
        """
        1. 接入真实开奖数据采集脚本
        2. 增加近 30 期 / 50 期趋势图
        3. 给 AI 分析区接入缓存后的轻量模型
        4. 增加简单密码访问控制
        """
    )

with right:
    st.subheader("数据更新状态")
    update_logs = load_recent_update_logs(limit=6)
    if update_logs.empty:
        st.info("还没有执行过更新任务，当前页面展示的是样例数据。")
    else:
        st.dataframe(
            _format_home_update_logs(update_logs),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("状态含义：已更新为成功写入新数据，已存在，已跳过为当前期号已在库中，更新失败为抓取或解析失败。")
