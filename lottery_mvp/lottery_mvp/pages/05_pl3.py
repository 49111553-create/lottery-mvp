import streamlit as st

from components.header import render_global_styles, render_sidebar
from db import init_db
from services.access_service import ensure_session_defaults
from services.page_renderers import render_lottery_workspace


st.set_page_config(page_title="排列3 | 多彩种分析 Pro", page_icon="🎯", layout="wide")
init_db()
ensure_session_defaults()
render_global_styles()
render_sidebar()
render_lottery_workspace("pl3")
