import streamlit as st


def render_metric_row(items: list[dict]):
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        with col:
            st.markdown(
                f"""
                <div style="padding:18px 18px 16px;border:1px solid rgba(15,23,42,0.08);
                border-radius:16px;background:linear-gradient(180deg,#ffffff 0%,#f8fafc 100%);
                min-height:110px">
                    <div style="font-size:13px;color:#475569">{item['label']}</div>
                    <div style="font-size:28px;font-weight:800;color:#0f172a;margin-top:10px">{item['value']}</div>
                    <div style="font-size:12px;color:#64748b;margin-top:10px">{item.get('help', '')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
