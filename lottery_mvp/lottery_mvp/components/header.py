import streamlit as st

from config import DB_LABEL
from services.access_service import (
    admin_sign_in,
    allowed_lottery_names,
    current_plan,
    is_member,
    login_with_code,
    logout,
)


GLOBAL_CSS = """
<style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(217,119,6,0.10), transparent 28%),
            linear-gradient(180deg, #f8fafc 0%, #eef2ff 45%, #f8fafc 100%);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }
    h1, h2, h3 {
        letter-spacing: 0;
    }
    .section-kicker {
        display:inline-block;
        color:#9a3412;
        font-size:12px;
        font-weight:700;
        text-transform:uppercase;
        letter-spacing:0.08em;
        margin-bottom:10px;
    }
</style>
"""


def render_global_styles():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown("### 多彩种分析 Pro")
        st.caption("低成本上线版的第二版工作台")
        st.caption(f"数据引擎：{DB_LABEL}")
        if not is_member():
            code = st.text_input("访问码", placeholder="输入付费访问码")
            if st.button("会员登录", use_container_width=True):
                ok, msg = login_with_code(code)
                if ok:
                    st.success(msg)
                    st.rerun()
                st.error(msg)
            st.info("演示访问码：FREE-DEMO")
        else:
            st.success(f"已登录：{current_plan()} 会员")
            st.caption(f"访问码：{st.session_state.get('access_code', '')}")
            if current_plan() == "paid":
                st.caption("已开通彩种：" + "、".join(allowed_lottery_names()))
            if st.button("退出登录", use_container_width=True):
                logout()
                st.rerun()
        st.divider()
        st.caption("管理员入口")
        admin_pwd = st.text_input("后台密码", type="password")
        if st.button("进入管理员后台", use_container_width=True):
            if admin_sign_in(admin_pwd):
                st.success("管理员验证成功")
            else:
                st.error("后台密码不正确")
