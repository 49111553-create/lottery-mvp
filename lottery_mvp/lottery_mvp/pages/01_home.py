import streamlit as st

from components.header import render_global_styles, render_sidebar
from components.number_balls import render_number_balls
from components.summary_cards import render_metric_row
from db import get_dashboard_summary, init_db
from services.access_service import ensure_session_defaults
from services.draw_service import get_home_cards


st.set_page_config(page_title="首页 | 多彩种分析 Pro", page_icon="🎯", layout="wide")
init_db()
ensure_session_defaults()
render_global_styles()
render_sidebar()

st.markdown("<span class='section-kicker'>会员分析门户</span>", unsafe_allow_html=True)
st.title("多彩种低成本云端网页 · 第二版")
st.caption("把查询、统计、会员收费、后台和更新状态收在一个更像正式产品的界面里。")

summary = get_dashboard_summary()
render_metric_row(
    [
        {"label": "累计开奖记录", "value": summary["total_draws"], "help": "覆盖 7 个彩种"},
        {"label": "有效访问码", "value": summary["active_codes"], "help": "用于付费访问控制"},
        {"label": "待处理订单", "value": summary["pending_orders"], "help": "管理员后台可发码"},
        {"label": "最近更新", "value": summary["last_update"], "help": "由 GitHub Actions 或 Render 任务驱动"},
    ]
)

hero_left, hero_right = st.columns([1.2, 0.8], gap="large")
with hero_left:
    st.markdown("#### 今日产品状态")
    st.markdown(
        """
        - 免费用户可以浏览全部彩种的基础预览，每天 AI 3 次
        - 9.9 元月卡可任选 3 个彩种开通，每天 AI 10 次
        - 数据更新优先抓取官方页面，失败时保留回退与日志记录
        """
    )
    st.info("当前定位是数据统计、趋势观察和娱乐选号服务，不承诺中奖。")
with hero_right:
    st.markdown("#### 会员权益")
    st.markdown(
        """
        - 9.9 元 / 30 天
        - 限 3 个彩种
        - 完整遗漏分析、CSV 导出、AI 10 次/天
        """
    )

st.markdown("#### 彩种入口")
cards = get_home_cards()
for row_group in [cards[i:i + 3] for i in range(0, len(cards), 3)]:
    cols = st.columns(len(row_group), gap="large")
    for col, item in zip(cols, row_group):
        with col:
            st.markdown(
                f"""
                <div style="padding:18px;border-radius:18px;background:rgba(255,255,255,0.82);
                border:1px solid rgba(15,23,42,0.08);min-height:160px">
                    <div style="font-size:13px;color:#9a3412;font-weight:700">{item['name']}</div>
                    <div style="font-size:22px;color:#0f172a;font-weight:800;margin-top:8px">第 {item['issue']} 期</div>
                    <div style="font-size:13px;color:#64748b;margin-top:6px">开奖日期 {item['draw_date']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_number_balls(item["numbers_main"], item["numbers_extra"])

st.markdown("#### 使用建议")
st.markdown(
    """
    第二版已经具备更像正式产品的结构：首页概览、独立彩种页、会员页、管理员后台、更新与抓取日志。
    接下来最重要的是把真实开奖源再稳一层，然后再做更细的页面视觉强化。
    """
)
