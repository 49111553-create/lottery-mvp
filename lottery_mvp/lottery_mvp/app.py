import streamlit as st

from components.header import render_global_styles, render_sidebar
from db import init_db
from services.access_service import ensure_session_defaults, is_member


st.set_page_config(page_title="多彩种分析 Pro", page_icon="🎯", layout="wide")
init_db()
ensure_session_defaults()
render_global_styles()
render_sidebar()

st.markdown("<span class='section-kicker'>第二版总览</span>", unsafe_allow_html=True)
st.title("多彩种低成本云端网页 · 第二版")
st.caption("这一版把产品拆成独立页面、服务层和后台工作台，适合继续往正式收费产品推进。")

hero_left, hero_right = st.columns([1.2, 0.8], gap="large")
with hero_left:
    st.markdown(
        """
        ### 现在可以直接做的事
        - 进入左侧页面导航查看 7 个彩种的独立分析页
        - 进入会员页登记付款并走访问码开通流程
        - 进入管理员后台查看更新结果、抓取日志和手动补录入口
        """
    )
    st.info("如果你要的是“能收费、能查询、能更新”的正式原型，这一版已经比第一版更接近产品。")
with hero_right:
    st.markdown(
        """
        #### 当前账号状态
        - 访问权限：{status}
        - 页面结构：独立首页 / 彩种页 / 会员页 / 后台
        - 数据层：支持 SQLite，后续可切 PostgreSQL
        """.format(status="会员已登录" if is_member() else "未登录")
    )

st.markdown("#### 页面导航")
st.markdown(
    """
    左侧 `Pages` 菜单已经拆出：
    - 首页
    - 7 个彩种分析页
    - 会员开通页
    - 管理员后台
    """
)
