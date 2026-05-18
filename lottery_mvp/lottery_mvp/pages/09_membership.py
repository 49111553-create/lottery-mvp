import streamlit as st

from components.header import render_global_styles, render_sidebar
from db import create_order, init_db
from services.access_service import ensure_session_defaults


st.set_page_config(page_title="会员开通 | 多彩种分析 Pro", page_icon="🎯", layout="wide")
init_db()
ensure_session_defaults()
render_global_styles()
render_sidebar()

st.markdown("<span class='section-kicker'>会员开通</span>", unsafe_allow_html=True)
st.title("付费访问与会员权益")
st.caption("保留低成本收款方式，同时把付费逻辑做成更清楚的单独页面。")

left, right = st.columns([1.15, 0.85], gap="large")
with left:
    st.markdown("#### 套餐方案")
    st.markdown(
        """
        - 9.9 元月卡：有效期 30 天，限 3 个彩种
        - 所有套餐均为“网站访问权限 + 数据分析服务”
        """
    )
    st.markdown("#### 权益对比")
    st.table(
        {
            "功能": ["可查看彩种", "历史查询", "CSV 导出", "遗漏分析", "AI 次数", "模拟选号"],
            "免费版": ["全部彩种预览", "最近 10 期", "不支持", "摘要", "3 次/天", "支持"],
            "9.9 元月卡": ["限 3 个彩种", "完整", "支持", "完整", "10 次/天", "支持"],
        }
    )
    st.caption("开通后由管理员为你勾选 3 个可访问彩种。")
with right:
    st.markdown("#### 付款登记")
    with st.form("membership_form"):
        payer_name = st.text_input("付款昵称")
        channel = st.selectbox("支付方式", ["微信", "支付宝"])
        amount = st.selectbox("套餐金额", [9.9])
        preferred_lotteries = st.multiselect(
            "希望开通的彩种（最多 3 个）",
            options=["双色球", "大乐透", "福彩3D", "排列3", "排列5", "七乐彩", "快乐8"],
            max_selections=3,
        )
        payment_note = st.text_input("付款备注 / 订单号")
        submitted = st.form_submit_button("提交登记")
        if submitted:
            extra_note = payment_note
            if preferred_lotteries:
                extra_note = f"{payment_note} | 彩种偏好: {'/'.join(preferred_lotteries)}"
            create_order(payer_name, channel, extra_note, float(amount))
            st.success("已登记付款信息，管理员后台可发放访问码。")
    st.info("建议把你的微信 / 支付宝收款码截图放在这里，形成完整开通页。")

st.warning("所有分析仅用于统计观察、娱乐选号与产品服务，不承诺中奖。")
