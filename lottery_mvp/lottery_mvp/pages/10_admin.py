import pandas as pd
import streamlit as st

from components.header import render_global_styles, render_sidebar
from config import DEFAULT_PAID_ALLOWED_COUNT, LOTTERY_CONFIG
from db import init_db
from services.access_service import ensure_session_defaults
from services.admin_service import (
    dashboard_data,
    disable_code,
    extend_code,
    generate_codes,
    get_admin_lists,
    issue_code_for_order,
    run_seed,
    run_update,
    save_manual_draw,
)


st.set_page_config(page_title="管理员后台 | 多彩种分析 Pro", page_icon="🎯", layout="wide")
init_db()
ensure_session_defaults()
render_global_styles()
render_sidebar()

if not st.session_state.get("admin_ok"):
    st.warning("请先在侧边栏输入后台密码后再进入管理员页面。")
    st.stop()

st.markdown("<span class='section-kicker'>管理员后台</span>", unsafe_allow_html=True)
st.title("运营与数据控制台")
st.caption("统一查看订单、访问码、抓取日志、更新结果和手动补录入口。")

summary = dashboard_data()
cols = st.columns(4)
cols[0].metric("有效访问码", summary["active_codes"])
cols[1].metric("待处理订单", summary["pending_orders"])
cols[2].metric("今日 AI 次数", summary["ai_today"])
cols[3].metric("累计开奖记录", summary["total_draws"])

tabs = st.tabs(["仪表盘", "订单与访问码", "数据更新", "抓取日志", "手动补录"])
lists = get_admin_lists()

with tabs[0]:
    st.dataframe(pd.DataFrame(lists["update_logs"]), use_container_width=True, hide_index=True)
    st.markdown("#### 最近后台动作")
    st.dataframe(pd.DataFrame(lists["admin_actions"]), use_container_width=True, hide_index=True)

with tabs[1]:
    left, right = st.columns([0.9, 1.1], gap="large")
    with left:
        st.markdown("#### 批量生成访问码")
        count = st.number_input("生成数量", min_value=1, max_value=100, value=10)
        days_valid = st.number_input("有效天数", min_value=1, max_value=365, value=30)
        plan_type = st.selectbox("套餐类型", ["paid", "free"])
        allowed_lotteries = st.multiselect(
            "开通彩种（付费码最多 3 个）",
            options=list(LOTTERY_CONFIG.keys()),
            default=["ssq", "dlt", "fc3d"] if plan_type == "paid" else list(LOTTERY_CONFIG.keys()),
            format_func=lambda x: LOTTERY_CONFIG[x]["name"],
            max_selections=DEFAULT_PAID_ALLOWED_COUNT if plan_type == "paid" else len(LOTTERY_CONFIG),
        )
        note = st.text_input("备注")
        if st.button("生成访问码"):
            if plan_type == "paid" and len(allowed_lotteries) != DEFAULT_PAID_ALLOWED_COUNT:
                st.error("9.9 元月卡必须指定 3 个彩种。")
            else:
                codes = generate_codes(int(count), plan_type, int(days_valid), note, allowed_lotteries)
                st.code("\n".join(codes))
        code_to_disable = st.text_input("停用访问码")
        if st.button("停用该访问码"):
            disable_code(code_to_disable)
            st.success("已停用")
        code_to_extend = st.text_input("延期访问码")
        extend_days = st.number_input("延期天数", min_value=1, max_value=365, value=30)
        if st.button("执行延期"):
            if extend_code(code_to_extend, int(extend_days)):
                st.success("访问码已延期")
            else:
                st.error("未找到该访问码")
    with right:
        st.markdown("#### 订单处理")
        st.dataframe(pd.DataFrame(lists["orders"]), use_container_width=True, hide_index=True)
        with st.form("issue_code_form_v2"):
            order_id = st.number_input("订单 ID", min_value=1, step=1)
            issued_code = st.text_input("发放的访问码")
            submit_issue = st.form_submit_button("标记已发码")
            if submit_issue:
                issue_code_for_order(int(order_id), issued_code)
                st.success("订单已标记为已发码")
        st.markdown("#### 当前访问码")
        st.dataframe(pd.DataFrame(lists["codes"]), use_container_width=True, hide_index=True)

with tabs[2]:
    st.markdown("#### 更新任务")
    c1, c2 = st.columns(2)
    if c1.button("初始化演示数据"):
        st.success(f"已写入 {run_seed()} 条演示记录")
    if c2.button("执行一次更新"):
        st.success(f"本次更新写入 {run_update()} 条记录")
    st.caption("正式环境下优先尝试官方源，失败时按环境变量决定是否回退。")

with tabs[3]:
    st.dataframe(pd.DataFrame(lists["fetch_logs"]), use_container_width=True, hide_index=True)

with tabs[4]:
    st.markdown("#### 手动补录开奖")
    with st.form("manual_draw_form"):
        lottery_type = st.selectbox("彩种", list(LOTTERY_CONFIG.keys()), format_func=lambda x: LOTTERY_CONFIG[x]["name"])
        issue = st.text_input("期号")
        draw_date = st.date_input("开奖日期")
        numbers_main = st.text_input("主号", placeholder="例如 03,08,12,19,22,31")
        numbers_extra = st.text_input("附加号", placeholder="例如 09")
        submitted = st.form_submit_button("保存开奖")
        if submitted:
            save_manual_draw(
                lottery_type,
                issue,
                draw_date.isoformat(),
                numbers_main,
                numbers_extra,
            )
            st.success("开奖数据已保存")
