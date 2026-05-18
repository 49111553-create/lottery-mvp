from datetime import date

import streamlit as st

from components.number_balls import render_number_balls
from components.summary_cards import render_metric_row
from config import LOTTERY_CONFIG
from services.access_service import (
    allowed_lottery_names,
    can_access_lottery,
    can_export_csv,
    can_view_full_history,
    current_plan,
)
from services.ai_service import (
    build_daily_summary,
    build_number_comment,
    build_recent_trend_summary,
    consume_ai_usage,
    get_usage_status,
)
from services.draw_service import export_draws_csv, get_filtered_draws, get_latest_draws
from services.stats_service import (
    build_number_plan,
    calc_odd_even_stats,
    calc_sum_stats,
    calc_zone_stats,
    get_frequency_stats,
    get_omission_stats,
)


def render_lottery_workspace(lottery_type: str):
    cfg = LOTTERY_CONFIG[lottery_type]
    lottery_name = cfg["name"]
    if not can_access_lottery(lottery_type):
        st.markdown("<span class='section-kicker'>访问受限</span>", unsafe_allow_html=True)
        st.title(f"{lottery_name} 暂未开通")
        st.warning("你当前的 9.9 元月卡仅限 3 个彩种。")
        st.info("当前已开通：" + "、".join(allowed_lottery_names()))
        st.stop()
    df = get_filtered_draws(lottery_type, limit=120 if can_view_full_history() else 10)
    latest_df = get_latest_draws(lottery_type, 5)
    latest = latest_df.iloc[0] if not latest_df.empty else None

    st.markdown("<span class='section-kicker'>彩种分析台</span>", unsafe_allow_html=True)
    st.title(lottery_name)
    st.caption("围绕历史查询、频率分布、遗漏观察、娱乐选号和 AI 解释做统一展示。")

    render_metric_row(
        [
            {"label": "会员状态", "value": "会员版" if can_view_full_history() else "免费版", "help": "会员可查看完整历史与导出"},
            {"label": "可用彩种", "value": 3 if current_plan() == "paid" else 7, "help": "9.9 元月卡限制 3 个彩种"},
            {"label": "最近一期", "value": latest["issue"] if latest is not None else "-", "help": latest["draw_date"] if latest is not None else "暂无"},
            {"label": "展示条数", "value": len(df), "help": "免费用户默认显示 10 期"},
            {"label": "今日日期", "value": date.today().isoformat(), "help": "统计观察每日刷新"},
        ]
    )

    if latest is not None:
        st.markdown("#### 最新开奖")
        render_number_balls(str(latest["numbers_main"]), str(latest["numbers_extra"]))

    query_col, insight_col = st.columns([1.2, 0.8], gap="large")
    with query_col:
        st.markdown("#### 历史查询")
        filter_cols = st.columns(3)
        issue_keyword = filter_cols[0].text_input("按期号查询")
        start_date = filter_cols[1].text_input("开始日期", placeholder="YYYY-MM-DD")
        end_date = filter_cols[2].text_input("结束日期", placeholder="YYYY-MM-DD")
        limit = 100 if can_view_full_history() else 10
        filtered = get_filtered_draws(
            lottery_type,
            issue_keyword=issue_keyword,
            start_date=start_date or None,
            end_date=end_date or None,
            limit=limit,
        )
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        if can_export_csv():
            st.download_button(
                "导出当前筛选 CSV",
                data=export_draws_csv(filtered),
                file_name=f"{lottery_type}_history.csv",
                mime="text/csv",
            )
        else:
            st.caption("CSV 导出为会员权益。")

    with insight_col:
        st.markdown("#### 统计速览")
        odd_even = calc_odd_even_stats(df)
        zones = calc_zone_stats(df, lottery_type)
        sums = calc_sum_stats(df)
        st.metric("奇偶比", f"{odd_even['odd']} : {odd_even['even']}")
        st.metric("和值均值", sums["avg"])
        st.metric("三区分布", f"{zones['一区']}/{zones['二区']}/{zones['三区']}")

    tab1, tab2, tab3, tab4 = st.tabs(["频率统计", "遗漏分析", "模拟选号", "AI 辅助分析"])
    with tab1:
        period = st.segmented_control("统计范围", options=[10, 30, 50, 100], default=30)
        freq = get_frequency_stats(df, lottery_type, int(period))
        hot = freq.sort_values("count", ascending=False).head(8) if not freq.empty else freq
        c1, c2 = st.columns([1.2, 0.8], gap="large")
        with c1:
            st.dataframe(freq, use_container_width=True, hide_index=True)
            if not freq.empty:
                st.bar_chart(freq.set_index("number")["count"], use_container_width=True)
        with c2:
            st.markdown("#### 热门号")
            for _, row in hot.iterrows():
                st.write(f"{int(row['number'])} 号 · 出现 {int(row['count'])} 次")

    with tab2:
        omission = get_omission_stats(df, lottery_type, min(len(df), 100) or 10)
        if can_view_full_history():
            st.dataframe(omission, use_container_width=True, hide_index=True)
        else:
            st.info("免费版可浏览摘要，完整遗漏表为会员权益。")
            st.dataframe(omission.head(12), use_container_width=True, hide_index=True)

    with tab3:
        mode = st.segmented_control("选号模式", options=["随机生成", "冷热均衡", "区间均衡"], default="冷热均衡")
        if st.button("生成模拟号码", key=f"sim_{lottery_type}"):
            plan = build_number_plan(lottery_type, mode)
            render_number_balls(plan["main"], plan["extra"])
            st.write(plan["reason"])
            st.caption("模拟号码仅供娱乐和参考。")

    with tab4:
        actor_key, used, limit_ai, allowed = get_usage_status()
        st.caption(f"当前套餐：{current_plan()} | 今日 AI 次数：{used}/{limit_ai}")
        ai_action = st.radio("AI 模式", ["今日分析", "近 30 期趋势", "号码结构点评"], horizontal=True)
        custom_main = st.text_input("号码点评主号", placeholder="例如 03,07,12,19,22,31", key=f"main_{lottery_type}")
        custom_extra = st.text_input("号码点评附加号", placeholder="例如 09", key=f"extra_{lottery_type}")
        if st.button("生成 AI 结果", key=f"ai_{lottery_type}"):
            ok, used_after, limit_after = consume_ai_usage(lottery_type, ai_action)
            if not ok:
                st.error("今日 AI 次数已用完。")
            else:
                if ai_action == "今日分析":
                    st.write(build_daily_summary(lottery_type, lottery_name, df))
                elif ai_action == "近 30 期趋势":
                    st.write(build_recent_trend_summary(lottery_type, lottery_name, df, 30))
                else:
                    st.write(build_number_comment(lottery_name, custom_main or "03,08,12", custom_extra))
                st.caption(f"已使用 {used_after}/{limit_after} 次。")
