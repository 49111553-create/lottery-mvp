import streamlit as st


def _ball(number: str, bg: str):
    return (
        f"<span style='display:inline-flex;align-items:center;justify-content:center;"
        f"width:34px;height:34px;border-radius:999px;background:{bg};color:white;"
        f"font-weight:700;margin-right:8px;margin-bottom:8px;box-shadow:0 6px 18px rgba(0,0,0,0.16);'>{number}</span>"
    )


def render_number_balls(numbers_main: str, numbers_extra: str = "", extra_color: str = "#0f62fe"):
    main_html = "".join(_ball(number, "#d92d20") for number in numbers_main.split(",") if number)
    extra_html = "".join(_ball(number, extra_color) for number in numbers_extra.split(",") if number)
    st.markdown(f"<div style='padding-top:4px'>{main_html}{extra_html}</div>", unsafe_allow_html=True)
