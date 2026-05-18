from datetime import datetime

import streamlit as st

from config import DB_LABEL, LOTTERY_OPTIONS
from data_service import (
    build_ai_summary,
    export_csv,
    frequency_stats,
    load_draws,
    omission_stats,
    run_daily_update,
    seed_demo_data,
    simulate_numbers,
)
from db import (
    admin_login,
    create_access_codes,
    create_order,
    disable_access_code,
    get_access_codes,
    get_ai_limit,
    get_ai_usage_count,
    get_orders,
    get_update_logs,
    init_db,
    log_ai_usage,
    mark_order_issued,
    verify_access_code,
)


st.set_page_config(page_title="多彩种低成本云端网页 MVP", page_icon="🎯", layout="wide")
init_db()


def ensure_session_defaults():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("access_code", "")
    st.session_state.setdefault("plan_type", "free")
    st.session_state.setdefault("admin_ok", False)


def sidebar_auth():
    with st.sidebar:
        st.title("多彩种分析 MVP")
        st.caption("统计观察、娱乐选号、轻量收费")
        st.caption(f"当前数据库：{DB_LABEL}")
        if not st.session_state["logged_in"]:
            code = st.text_input("输入访问码", placeholder="例如 FREE-DEMO")
            if st.button("访问网站", use_container_width=True):
                ok, msg, row = verify_access_code(code, device_key="streamlit-browser")
                if ok:
                    st.session_state["logged_in"] = True
                    st.session_state["access_code"] = code
                    st.session_state["plan_type"] = row["plan_type"]
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            st.info("演示访问码：FREE-DEMO")
        else:
            st.success(f"已登录：{st.session_state['access_code']}")
            st.write(f"套餐：{st.session_state['plan_type']}")
            if st.button("退出登录", use_container_width=True):
                st.session_state["logged_in"] = False
                st.session_state["access_code"] = ""
                st.session_state["plan_type"] = "free"
                st.rerun()

        st.divider()
        admin_pwd = st.text_input("管理员密码", type="password")
        if st.button("进入后台", use_container_width=True):
            st.session_state["admin_ok"] = admin_login(admin_pwd)
            if not st.session_state["admin_ok"]:
                st.error("管理员密码不正确")


def render_access_paywall():
    st.title("访问码收费 MVP")
    left, right = st.columns([1.4, 1])
    with left:
        st.markdown(
            """
            这是一个面向多彩种的低成本分析站原型，当前支持：
            - 双色球、大乐透、福彩3D、排列3、排列5、七乐彩、快乐8
            - 历史开奖查询、频率统计、遗漏分析、模拟选号
            - AI 辅助分析、CSV 导出、访问码收费、管理员后台

            付费方式建议先用 9.9 元手工发码：
            - 用户扫码付款
            - 填写付款备注
            - 管理员后台发放访问码
            """
        )
        with st.form("pay_form"):
            payer_name = st.text_input("付款人昵称")
            channel = st.selectbox("支付方式", ["微信", "支付宝"])
            note = st.text_input("付款备注 / 订单号")
            submitted = st.form_submit_button("提交付款登记")
            if submitted:
                create_order(payer_name, channel, note, 9.9)
                st.success("已登记，管理员可在后台发码。")
    with right:
        st.metric("会员价格", "9.9 元")
        st.metric("免费版 AI 次数", "1 次/天")
        st.metric("付费版 AI 次数", "5 次/天")
        st.warning("提示：本站定位为数据分析与娱乐参考，不承诺中奖。")


def render_lottery_page():
    st.title("多彩种分析")
    selected_name = st.selectbox("选择彩种", list(LOTTERY_OPTIONS.keys()))
    lottery_type = LOTTERY_OPTIONS[selected_name]
    df = load_draws(lottery_type, limit=200)

    c1, c2, c3 = st.columns(3)
    c1.metric("历史记录", len(df))
    c2.metric("最近一期", df.iloc[0]["issue"] if not df.empty else "-")
    c3.metric("最近日期", df.iloc[0]["draw_date"] if not df.empty else "-")

    filter_col1, filter_col2 = st.columns([1, 2])
    with filter_col1:
        recent_n = st.slider("最近 N 期", 10, 200, 50, 10)
        keyword = st.text_input("按期号筛选")
    if keyword:
        df_show = df[df["issue"].astype(str).str.contains(keyword)]
    else:
        df_show = df.head(recent_n)

    tabs = st.tabs(["历史开奖", "频率统计", "遗漏分析", "模拟选号", "AI 辅助分析"])
    with tabs[0]:
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.download_button(
            "导出当前结果 CSV",
            data=export_csv(df_show),
            file_name=f"{lottery_type}_history.csv",
            mime="text/csv",
        )
    with tabs[1]:
        freq = frequency_stats(df_show)
        st.dataframe(freq, use_container_width=True, hide_index=True)
        if not freq.empty:
            st.bar_chart(freq.set_index("number")["count"], use_container_width=True)
    with tabs[2]:
        omission = omission_stats(df_show, lottery_type)
        st.dataframe(omission, use_container_width=True, hide_index=True)
    with tabs[3]:
        mode = st.radio("选号模式", ["随机生成", "冷热均衡"], horizontal=True)
        if st.button("生成模拟号码"):
            main, extra = simulate_numbers(lottery_type, mode)
            text = f"主号：{main}"
            if extra:
                text += f" | 附加号：{extra}"
            st.success(text)
            st.caption("仅供娱乐和参考。")
    with tabs[4]:
        actor_key = st.session_state["access_code"] or "guest"
        plan_type = st.session_state["plan_type"]
        used = get_ai_usage_count(actor_key)
        limit = get_ai_limit(plan_type)
        st.info(f"今日 AI 次数：{used} / {limit}")
        if st.button("生成 AI 分析摘要"):
            if used >= limit:
                st.error("今日 AI 次数已用完。")
            else:
                summary = build_ai_summary(df_show, selected_name)
                log_ai_usage(actor_key, st.session_state["access_code"], lottery_type, "summary")
                st.write(summary)


def render_admin():
    if not st.session_state["admin_ok"]:
        return
    st.title("管理员后台")
    tabs = st.tabs(["访问码生成", "订单与发码", "数据更新", "运行日志"])

    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        count = col1.number_input("生成数量", min_value=1, max_value=100, value=10)
        days_valid = col2.number_input("有效天数", min_value=1, max_value=365, value=30)
        plan_type = col3.selectbox("套餐", ["paid", "free"])
        note = st.text_input("备注")
        if st.button("生成访问码"):
            codes = create_access_codes(int(count), plan_type=plan_type, days_valid=int(days_valid), note=note)
            st.success("已生成访问码")
            st.code("\n".join(codes))
        st.dataframe(
            get_access_codes(),
            use_container_width=True,
            hide_index=True,
        )
        code_to_disable = st.text_input("停用访问码")
        if st.button("停用"):
            disable_access_code(code_to_disable)
            st.success("已停用")

    with tabs[1]:
        st.dataframe(get_orders(), use_container_width=True, hide_index=True)
        with st.form("issue_code_form"):
            order_id = st.number_input("订单 ID", min_value=1, step=1)
            issued_code = st.text_input("已发放访问码")
            submit_issue = st.form_submit_button("标记已发码")
            if submit_issue:
                mark_order_issued(int(order_id), issued_code)
                st.success("订单已更新")

    with tabs[2]:
        st.write("支持演示数据初始化和每日数据更新入口。更新时会优先尝试官方源。")
        col1, col2 = st.columns(2)
        if col1.button("初始化演示数据"):
            seeded = seed_demo_data()
            st.success(f"已写入 {seeded} 条演示数据")
        if col2.button("执行一次数据更新"):
            updated = run_daily_update()
            st.success(f"本次更新写入 {updated} 条数据")
        st.caption("若官方源不可访问，可通过环境变量关闭或保留演示回退。")

    with tabs[3]:
        st.dataframe(get_update_logs(), use_container_width=True, hide_index=True)


def render_footer():
    st.divider()
    st.caption(
        f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        "本网站仅用于历史数据统计、趋势观察和娱乐参考，不构成中奖承诺。"
    )


ensure_session_defaults()
sidebar_auth()

main_tab, admin_tab = st.tabs(["用户前台", "管理员后台"])
with main_tab:
    if st.session_state["logged_in"]:
        render_lottery_page()
    else:
        render_access_paywall()
with admin_tab:
    render_admin()

render_footer()
