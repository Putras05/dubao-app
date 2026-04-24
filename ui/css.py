import streamlit as st


def _theme_css(T: dict) -> str:
    return f"""<style>
/* ══ APP BACKGROUND ══════════════════════════════════════════════════════════ */
.stApp {{ background: {T['bg_app']} !important; color: {T['text_primary']} !important; }}
[data-testid="stMain"] .block-container {{ background: transparent !important; color: {T['text_primary']} !important; }}

/* sidebar handled by _SIDEBAR_CSS — injected separately */

/* ══ MAIN CONTENT BUTTONS ════════════════════════════════════════════════════ */
[data-testid="stMain"] .stButton > button {{
    background: {T['bg_elevated']} !important;
    color: {T['text_primary']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 8px !important; font-weight: 600 !important;
    transition: all .14s !important;
}}
[data-testid="stMain"] .stButton > button:hover {{
    background: {T['accent']} !important;
    color: #ffffff !important;
    border-color: {T['accent']} !important;
}}

/* ══ METRIC CARDS ════════════════════════════════════════════════════════════ */
[data-testid="stMetric"] {{
    background: {T['bg_card']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 12px !important;
    box-shadow: {T['shadow_sm']} !important;
}}
[data-testid="stMetricLabel"] p {{ color: {T['text_secondary']} !important; }}
[data-testid="stMetricValue"] {{ color: {T['text_primary']} !important; }}
[data-testid="stMetricDelta"] {{ color: {T['text_secondary']} !important; }}

/* ══ PAGE HEADER BANNER ══════════════════════════════════════════════════════ */
.page-header {{
    background: {T['banner_bg']} !important;
    border-radius: 14px !important;
    box-shadow: {T['shadow_md']} !important;
    border: none !important;
}}
.page-header h1 {{ color: {T['banner_text']} !important; }}
.page-header p  {{ color: {T['banner_subtext']} !important; }}

/* ══ SECTION HEADER ═════════════════════════════════════════════════════════ */
.sec-hdr {{
    color: {T['text_secondary']} !important;
    background: {T['bg_elevated']} !important;
    border-left: 4px solid {T['accent']} !important;
    padding: 5px 12px !important;
    border-radius: 0 6px 6px 0 !important;
    font-size: 10.5px !important; font-weight: 800 !important;
    letter-spacing: 1.2px !important; text-transform: uppercase !important;
    margin: 20px 0 12px !important;
}}

/* ══ TABS ════════════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {{
    background: {T['bg_elevated']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 10px !important; padding: 4px !important; gap: 6px !important;
}}
.stTabs [data-baseweb="tab"] {{
    color: {T['text_secondary']} !important; background: transparent !important;
    border-radius: 8px !important; padding: 10px 28px !important;
}}
.stTabs [aria-selected="true"] {{
    background: {T['bg_card']} !important;
    color: {T['text_primary']} !important;
    box-shadow: {T['shadow_sm']} !important;
}}
.stTabs [data-baseweb="tab-panel"] {{
    background: {T['bg_card']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 0 0 10px 10px !important; padding: 18px !important;
}}

/* ══ ALERT CARDS — dark mode override ═══════════════════════════════════════ */
{('''
.alert-buy  { background: #0D2B15 !important; border-color: #34D399 !important; color: #86EFAC !important; }
.alert-sell { background: #2B0D0D !important; border-color: #F87171 !important; color: #FCA5A5 !important; }
.alert-warn { background: #2B200D !important; border-color: #FCD34D !important; color: #FDE68A !important; }
.alert-neut { background: #1A2233 !important; border-color: #64748B !important; color: #CBD5E1 !important; }
/* FIX A2: Forecast card colors (up/down/flat) — dark mode override */
.up   { background: rgba(52,211,153,0.15) !important; color: #86EFAC !important; }
.down { background: rgba(248,113,113,0.15) !important; color: #FCA5A5 !important; }
.flat { background: rgba(148,163,184,0.15) !important; color: #CBD5E1 !important; }
''' if T.get('is_dark') else '')}

/* ══ DATAFRAMES — full theme-aware fix ══════════════════════════════════════ */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div,
[data-testid="stDataFrameResizable"],
[data-testid="stDataFrameResizable"] > div {{
    background: {T['bg_card']} !important;
    background-color: {T['bg_card']} !important;
}}
[data-testid="stDataFrame"] {{
    border: 1px solid {T['border']} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}}
[data-testid="stDataFrame"] iframe {{
    background: {T['bg_card']} !important;
    background-color: {T['bg_card']} !important;
}}
[data-testid="stDataFrame"] thead tr th,
[data-testid="stDataFrame"] [role="columnheader"] {{
    background: {T['bg_elevated']} !important;
    background-color: {T['bg_elevated']} !important;
    color: {T['text_secondary']} !important;
    border-bottom: 2px solid {T['border']} !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    padding: 10px 12px !important;
}}
[data-testid="stDataFrame"] tbody tr td,
[data-testid="stDataFrame"] [role="cell"],
[data-testid="stDataFrame"] [role="gridcell"] {{
    background: {T['bg_card']} !important;
    background-color: {T['bg_card']} !important;
    color: {T['text_primary']} !important;
    border-bottom: 1px solid {T['divider']} !important;
    padding: 8px 12px !important;
    font-size: 13px !important;
}}
[data-testid="stDataFrame"] [role="rowheader"] {{
    background: {T['bg_elevated']} !important;
    color: {T['text_secondary']} !important;
    font-weight: 600 !important;
}}
[data-testid="stDataFrame"] *:not([style*="color"]) {{
    color: {T['text_primary']} !important;
}}
[data-testid="stElementToolbar"],
[data-testid="stElementToolbar"] button {{
    background: {T['bg_card']} !important;
    color: {T['text_secondary']} !important;
    border-color: {T['border']} !important;
}}

/* ══ EXPANDERS ═══════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {{
    background: {T['bg_card']} !important;
    border: 1px solid {T['border']} !important; border-radius: 10px !important;
}}
[data-testid="stExpander"] summary {{
    color: {T['text_primary']} !important; font-weight: 600 !important;
    background: {T['bg_elevated']} !important;
}}
[data-testid="stExpander"] > div,
[data-testid="stExpander"] .streamlit-expanderContent,
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
    background: {T['bg_card']} !important;
    color: {T['text_primary']} !important;
}}
[data-testid="stExpander"] p,
[data-testid="stExpander"] li,
[data-testid="stExpander"] span:not(.katex *),
[data-testid="stExpander"] strong {{
    color: {T['text_primary']} !important;
}}
[data-testid="stExpander"] table {{
    background: {T['bg_card']} !important;
    border-collapse: collapse !important;
    width: 100% !important;
}}
[data-testid="stExpander"] th {{
    background: {T['bg_elevated']} !important;
    color: {T['text_secondary']} !important;
    padding: 6px 12px !important;
    border: 1px solid {T['border']} !important;
    font-size: 12px !important;
}}
[data-testid="stExpander"] td {{
    background: {T['bg_card']} !important;
    color: {T['text_primary']} !important;
    padding: 6px 12px !important;
    border: 1px solid {T['border']} !important;
    font-size: 13px !important;
}}
.katex, .katex * {{ color: {T['text_primary']} !important; }}

/* ══ INFO BOXES ══════════════════════════════════════════════════════════════ */
.info-box {{
    background: {T['bg_elevated']} !important;
    border-color: {T['border']} !important;
    color: {T['text_primary']} !important;
}}

/* ══ DOWNLOAD BUTTON ═════════════════════════════════════════════════════════ */
[data-testid="stMain"] [data-testid="stDownloadButton"] > button,
[data-testid="stMain"] .stDownloadButton > button {{
    background: {T['bg_card']} !important;
    background-color: {T['bg_card']} !important;
    color: {T['text_primary']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all .14s !important;
}}
[data-testid="stMain"] [data-testid="stDownloadButton"] > button *,
[data-testid="stMain"] .stDownloadButton > button * {{
    color: {T['text_primary']} !important;
    background: transparent !important;
}}
[data-testid="stMain"] [data-testid="stDownloadButton"] > button:hover,
[data-testid="stMain"] .stDownloadButton > button:hover {{
    background: {T['accent']} !important;
    color: #FFFFFF !important;
    border-color: {T['accent']} !important;
}}
[data-testid="stMain"] [data-testid="stDownloadButton"] > button:hover *,
[data-testid="stMain"] .stDownloadButton > button:hover * {{
    color: #FFFFFF !important;
}}

/* ══ PRESET CHIPS + ALL MAIN-AREA COLUMN BUTTONS ════════════════════════════ */
/* FIX 2026-04-23: chip/button trong column → pill oval viền xanh nhạt
   (nhất quán với chatbot page suggestion chips) */
[data-testid="stMain"] [data-testid="stColumn"] .stButton > button,
[data-testid="stMain"] [data-testid="column"] .stButton > button,
[data-testid="stMain"] [data-testid="stHorizontalBlock"] .stButton > button {{
    background: {'rgba(96,165,250,0.15)' if T.get('is_dark') else 'rgba(21,101,192,0.08)'} !important;
    background-color: {'rgba(96,165,250,0.15)' if T.get('is_dark') else 'rgba(21,101,192,0.08)'} !important;
    color: {T['accent']} !important;
    border: 1px solid {T['accent']} !important;
    border-radius: 20px !important;
    padding: 6px 14px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    min-height: 38px !important;
    transition: all .14s !important;
}}
[data-testid="stMain"] [data-testid="stColumn"] .stButton > button *,
[data-testid="stMain"] [data-testid="column"] .stButton > button *,
[data-testid="stMain"] [data-testid="stHorizontalBlock"] .stButton > button * {{
    color: {T['accent']} !important;
    background: transparent !important;
}}
[data-testid="stMain"] [data-testid="stColumn"] .stButton > button:hover,
[data-testid="stMain"] [data-testid="column"] .stButton > button:hover,
[data-testid="stMain"] [data-testid="stHorizontalBlock"] .stButton > button:hover {{
    background: {T['accent']} !important;
    color: #FFFFFF !important;
    border-color: {T['accent']} !important;
    box-shadow: 0 4px 12px {T['accent']}40 !important;
}}
[data-testid="stMain"] [data-testid="stColumn"] .stButton > button:hover *,
[data-testid="stMain"] [data-testid="column"] .stButton > button:hover *,
[data-testid="stMain"] [data-testid="stHorizontalBlock"] .stButton > button:hover * {{
    color: #FFFFFF !important;
}}

/* ══ DATE INPUT (main area) ══════════════════════════════════════════════════ */
[data-testid="stMain"] [data-baseweb="input"] {{
    background: {T['bg_card']} !important;
    background-color: {T['bg_card']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 20px !important;
    min-height: 40px !important;
    padding: 0 14px !important;
    transition: border-color .14s !important;
}}
[data-testid="stMain"] [data-baseweb="input"]:focus-within {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 0 2px {T['accent']}33 !important;
}}
[data-testid="stMain"] [data-baseweb="input"] input,
[data-testid="stMain"] [data-baseweb="input"] * {{
    background: transparent !important;
    background-color: transparent !important;
    color: {T['text_primary']} !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}}
[data-testid="stMain"] .stDateInput > div > div {{
    background: {T['bg_card']} !important;
    background-color: {T['bg_card']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 20px !important;
    min-height: 40px !important;
}}
[data-testid="stMain"] .stDateInput input,
[data-testid="stMain"] .stDateInput [data-baseweb="input"] * {{
    color: {T['text_primary']} !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    background: transparent !important;
}}
/* ══ SELECTBOX & NUMBER INPUT (main area) ════════════════════════════════════ */
[data-testid="stMain"] .stSelectbox > div > div,
[data-testid="stMain"] [data-testid="stSelectbox"] > div > div,
[data-testid="stMain"] [data-baseweb="select"] > div {{
    background: {T['bg_card']} !important;
    background-color: {T['bg_card']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 20px !important;
    color: {T['text_primary']} !important;
}}
[data-testid="stMain"] .stSelectbox > div > div *,
[data-testid="stMain"] [data-baseweb="select"] * {{
    background: transparent !important;
    color: {T['text_primary']} !important;
}}
[data-testid="stMain"] .stNumberInput > div > div,
[data-testid="stMain"] [data-testid="stNumberInput"] > div > div {{
    background: {T['bg_card']} !important;
    background-color: {T['bg_card']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 20px !important;
}}
[data-testid="stMain"] .stNumberInput input,
[data-testid="stMain"] [data-testid="stNumberInput"] input {{
    background: transparent !important;
    color: {T['text_primary']} !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}}
[data-testid="stMain"] [data-testid="stWidgetLabel"] p,
[data-testid="stMain"] label p, [data-testid="stMain"] label {{
    color: {T['text_secondary']} !important;
    font-size: 12px !important;
    font-weight: 600 !important;
}}

/* ══ METRIC CARDS — aggressive child selectors ═══════════════════════════════ */
[data-testid="stMain"] [data-testid="metric-container"],
[data-testid="stMain"] [data-testid="stMetric"] {{
    background: {T['bg_card']} !important;
    background-color: {T['bg_card']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 12px !important;
    box-shadow: {T['shadow_sm']} !important;
    padding: 14px 16px !important;
}}
[data-testid="stMain"] [data-testid="stMetricLabel"] *,
[data-testid="stMain"] [data-testid="stMetricLabel"] p {{
    color: {T['text_secondary']} !important;
    background: transparent !important;
}}
[data-testid="stMain"] [data-testid="stMetricValue"],
[data-testid="stMain"] [data-testid="stMetricValue"] * {{
    color: {T['text_primary']} !important;
    background: transparent !important;
}}
[data-testid="stMain"] [data-testid="stMetricDelta"] * {{
    background: transparent !important;
}}

/* ══ REFRESH HEADER BUTTON ═══════════════════════════════════════════════════ */
.refresh-header-btn .stButton > button,
.refresh-header-btn .stButton > button:focus,
.refresh-header-btn .stButton > button:active,
.refresh-header-btn .stButton > button:focus:not(:active) {{
    background: linear-gradient(135deg,#0D1F4A 0%,#1B3D8C 60%,#2756C0 100%) !important;
    background-image: linear-gradient(135deg,#0D1F4A 0%,#1B3D8C 60%,#2756C0 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    font-size: 22px !important;
    min-height: 60px !important;
    padding: 0 !important;
    transition: filter 0.2s ease, transform 0.2s ease !important;
    box-shadow: 0 2px 10px rgba(27,61,140,0.4) !important;
}}
.refresh-header-btn .stButton > button:hover {{
    filter: brightness(1.2) !important;
    transform: rotate(180deg) !important;
}}
.refresh-header-btn .stButton > button p,
.refresh-header-btn .stButton > button span {{
    color: #FFFFFF !important;
    background: transparent !important;
}}

/* ══ DATE PICKER CALENDAR POPUP ══════════════════════════════════════════════ */
[data-baseweb="calendar"],
[data-baseweb="calendar"] > div,
[data-baseweb="popover"] [data-baseweb="calendar"] {{
    background: {T['bg_card']} !important;
    background-color: {T['bg_card']} !important;
    color: {T['text_primary']} !important;
    border: 1px solid {T['border']} !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
    border-radius: 10px !important;
}}
[data-baseweb="calendar"] * {{
    color: {T['text_primary']} !important;
    background: transparent !important;
    background-color: transparent !important;
}}
[data-baseweb="calendar"] [role="button"]:hover {{
    background: {T['accent']}33 !important;
    background-color: {T['accent']}33 !important;
}}
[data-baseweb="calendar"] [aria-selected="true"] {{
    background: {T['accent']} !important;
    background-color: {T['accent']} !important;
    color: #FFFFFF !important;
}}
[data-baseweb="calendar"] [aria-current="date"] {{
    border: 1px solid {T['accent']} !important;
}}
[data-baseweb="calendar"] [role="columnheader"] {{
    color: {T['text_muted']} !important;
    font-weight: 700 !important;
}}

/* ══ BEST MODEL GLOW ANIMATION ═══════════════════════════════════════════════ */
@keyframes best-glow {{
    0%, 100% {{ box-shadow: 0 0 5px #F9A825, 0 0 10px rgba(249,168,37,0.3); }}
    50%       {{ box-shadow: 0 0 18px #F9A825, 0 0 35px rgba(249,168,37,0.5); }}
}}
.best-model-card {{ animation: best-glow 2.5s ease-in-out infinite; }}

/* ══ LIVE DOT ANIMATION ══════════════════════════════════════════════════════ */
@keyframes live-pulse {{
    0%, 100% {{ opacity:1; transform:scale(1); box-shadow:0 0 6px #10B981; }}
    50%       {{ opacity:.65; transform:scale(1.35); box-shadow:0 0 14px #10B981; }}
}}
.live-dot {{
    display:inline-block; width:8px; height:8px; border-radius:50%;
    background:#10B981; margin-right:5px; vertical-align:middle;
    animation: live-pulse 2s infinite;
}}

/* ══ SLIDER (main area) ══════════════════════════════════════════════════════ */
[data-testid="stMain"] [data-testid="stSlider"] {{
    padding: 4px 0 !important;
}}
[data-testid="stMain"] [data-testid="stSlider"] [data-testid="stTickBar"] > div,
[data-testid="stMain"] [data-testid="stSlider"] [data-testid="stTickBar"] * {{
    color: {T['text_secondary']} !important;
    font-size: 11px !important;
    font-weight: 700 !important;
}}
[data-testid="stMain"] [data-testid="stSlider"] [data-testid="stThumbValue"] p,
[data-testid="stMain"] [data-testid="stSlider"] output {{
    color: {T['accent']} !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    background: transparent !important;
}}
[data-testid="stMain"] [data-testid="stSlider"] [role="slider"] {{
    background: {T['accent']} !important;
    border: 2px solid {T['bg_card']} !important;
    box-shadow: 0 2px 8px {T['accent']}66 !important;
    width: 18px !important;
    height: 18px !important;
}}
[data-testid="stMain"] [data-testid="stSlider"] > div > div > div {{
    background: {T['border']} !important;
    height: 4px !important;
    border-radius: 2px !important;
}}
[data-testid="stMain"] [data-testid="stSlider"] > div > div > div > div {{
    background: {T['accent']} !important;
    height: 4px !important;
    border-radius: 2px !important;
}}

/* ══ HR ══════════════════════════════════════════════════════════════════════ */
hr {{ border-color: {T['border']} !important; }}

/* ══ FOCUS OUTLINES — Accessibility (Tab navigation) ═════════════════════════
   User dùng Tab/Shift-Tab điều hướng bàn phím sẽ thấy ring accent 2px.
   Chỉ hiện khi :focus-visible (click chuột không trigger, tránh ring thừa). */
.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible,
[data-testid="stTextInput"] input:focus-visible,
[data-testid="stNumberInput"] input:focus-visible,
[data-testid="stSelectbox"] [data-baseweb="select"]:focus-within,
[data-testid="stDateInput"] input:focus-visible,
[data-testid="stSlider"] [role="slider"]:focus-visible,
[data-testid="stChatInput"] textarea:focus-visible,
[data-baseweb="tab"]:focus-visible {{
    outline: 2px solid {T['accent']} !important;
    outline-offset: 2px !important;
    box-shadow: 0 0 0 4px {('rgba(96,165,250,0.22)' if T.get('is_dark') else 'rgba(21,101,192,0.18)')} !important;
}}
/* Loại bỏ outline cũ xấu của Streamlit default */
.stButton > button:focus:not(:focus-visible) {{ outline: none !important; }}

/* ══ SCROLLBAR ═══════════════════════════════════════════════════════════════
   Style custom để nhìn rõ ở cả dark/light mode, rộng hơn default cho 4K.
   Dark mode: accent-blue tint trên bg tối (contrast cao).
   Light mode: gray với hover accent. */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{
    background: {T['bg_elevated']};
    border-radius: 10px;
}}
::-webkit-scrollbar-thumb {{
    background: {('rgba(96,165,250,0.35)' if T.get('is_dark') else 'rgba(148,163,184,0.55)')};
    border-radius: 10px;
    border: 2px solid {T['bg_elevated']};
}}
::-webkit-scrollbar-thumb:hover {{
    background: {('rgba(96,165,250,0.65)' if T.get('is_dark') else 'rgba(96,165,250,0.70)')};
}}
::-webkit-scrollbar-corner {{ background: transparent; }}
* {{ scrollbar-width: thin; scrollbar-color: {('rgba(96,165,250,0.35) transparent' if T.get('is_dark') else 'rgba(148,163,184,0.55) transparent')}; }}

/* ══ OVERRIDE: HIGH-SPECIFICITY CHIP + DOWNLOAD BUTTON FIX ══════════════════ */
[data-testid="stMain"] div[data-testid="stHorizontalBlock"] .stButton > button {{
    background: {T['bg_card']} !important;
    background-color: {T['bg_card']} !important;
    color: {T['text_primary']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 20px !important;
    padding: 8px 16px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    min-height: 40px !important;
    transition: all 0.2s !important;
}}
[data-testid="stMain"] div[data-testid="stHorizontalBlock"] .stButton > button p {{
    color: {T['text_primary']} !important;
    background: transparent !important;
}}
[data-testid="stMain"] div[data-testid="stHorizontalBlock"] .stButton > button:hover {{
    background: {T['accent']} !important;
    background-color: {T['accent']} !important;
    color: #FFFFFF !important;
    border-color: {T['accent']} !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px {T['accent']}40 !important;
}}
[data-testid="stMain"] div[data-testid="stHorizontalBlock"] .stButton > button:hover p {{
    color: #FFFFFF !important;
    background: transparent !important;
}}
[data-testid="stMain"] div[data-testid="stDownloadButton"] > button,
[data-testid="stMain"] div .stDownloadButton > button {{
    background: {T['bg_card']} !important;
    background-color: {T['bg_card']} !important;
    color: {T['text_primary']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 10px !important;
    padding: 12px 20px !important;
    font-weight: 600 !important;
    width: 100% !important;
    min-height: 44px !important;
    transition: all 0.2s !important;
}}
[data-testid="stMain"] div[data-testid="stDownloadButton"] > button p,
[data-testid="stMain"] div .stDownloadButton > button p {{
    color: {T['text_primary']} !important;
    background: transparent !important;
}}
[data-testid="stMain"] div[data-testid="stDownloadButton"] > button:hover,
[data-testid="stMain"] div .stDownloadButton > button:hover {{
    background: {T['success']} !important;
    background-color: {T['success']} !important;
    color: #FFFFFF !important;
    border-color: {T['success']} !important;
}}
[data-testid="stMain"] div[data-testid="stDownloadButton"] > button:hover p,
[data-testid="stMain"] div .stDownloadButton > button:hover p {{
    color: #FFFFFF !important;
    background: transparent !important;
}}

/* ══ CHAT INPUT — theme-aware ════════════════════════════════════════════════ */
div[data-testid="stChatInput"] > div {{
    background: {T['bg_elevated']} !important;
    background-color: {T['bg_elevated']} !important;
    border: 2px solid {T['accent']} !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 12px {T['accent']}20 !important;
}}
div[data-testid="stChatInput"] > div:focus-within {{
    border-color: {T.get('accent_hover', T['accent'])} !important;
    box-shadow: 0 4px 16px {T['accent']}40 !important;
}}
div[data-testid="stChatInput"] textarea,
div[data-testid="stChatInput"] [contenteditable],
div[data-testid="stChatInput"] input {{
    color: {T['text_primary']} !important;
    background: transparent !important;
    caret-color: {T['accent']} !important;
}}
div[data-testid="stChatInput"] * {{
    color: {T['text_primary']} !important;
}}
div[data-testid="stChatInput"] button,
div[data-testid="stChatInput"] button svg {{
    color: {T['accent']} !important;
    fill: {T['accent']} !important;
}}

/* ══ CHAT STATUS — theme-aware colors (FIX A3) ═══════════════════════════════ */
{('''
.chat-status-ok {
    background: linear-gradient(90deg,rgba(52,211,153,.15) 0%,rgba(52,211,153,0) 100%) !important;
    border-color: rgba(52,211,153,.35) !important;
    color: #34D399 !important;
}
.chat-status-warn {
    background: linear-gradient(90deg,rgba(251,191,36,.15) 0%,rgba(251,191,36,0) 100%) !important;
    border-color: rgba(251,191,36,.35) !important;
    color: #FBBF24 !important;
}
''' if T.get('is_dark') else '''
.chat-status-ok {
    background: linear-gradient(90deg,rgba(16,185,129,.10) 0%,rgba(16,185,129,0) 100%) !important;
    border-color: rgba(16,185,129,.30) !important;
    color: #047857 !important;
}
.chat-status-warn {
    background: linear-gradient(90deg,rgba(245,158,11,.10) 0%,rgba(245,158,11,0) 100%) !important;
    border-color: rgba(245,158,11,.30) !important;
    color: #92400E !important;
}
''')}

/* ══ CHAT BUBBLE BOT — border visible in both modes ═════════════════════════ */
.chat-bubble-bot {{
    border: 1px solid {T['border_strong']} !important;
}}

/* ══ CHAT LABELS — readable in both modes ═══════════════════════════════════ */
.chat-label {{ color: {T['text_muted']} !important; }}
.chat-time  {{ color: {T['text_muted']} !important; }}

/* ══ ALL MAIN BUTTONS — legacy selectors + baseButton direct targeting ══════ */
[data-testid="stMain"] .stButton > button,
[data-testid="stMain"] .stButton > button p,
[data-testid="stMain"] .stButton > button span,
[data-testid="stMain"] .stButton > button div {{
    color: {T['text_primary']} !important;
}}
[data-testid="stMain"] .stButton > button[kind="primary"],
[data-testid="stMain"] .stButton > button[kind="primary"] p,
[data-testid="stMain"] .stButton > button[kind="primary"] span {{
    color: #FFFFFF !important;
    background: {T['accent']} !important;
    background-color: {T['accent']} !important;
    border-color: {T['accent']} !important;
}}

/* ══ baseButton — direct element targeting (Streamlit 1.3x+) ════════════════ */
[data-testid="stMain"] [data-testid*="baseButton"] {{
    background: {T['bg_elevated']} !important;
    background-color: {T['bg_elevated']} !important;
    color: {T['text_primary']} !important;
    border: 1px solid {T['border_strong']} !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all .14s !important;
}}
[data-testid="stMain"] [data-testid*="baseButton"] p,
[data-testid="stMain"] [data-testid*="baseButton"] span,
[data-testid="stMain"] [data-testid*="baseButton"] div {{
    color: {T['text_primary']} !important;
    background: transparent !important;
    background-color: transparent !important;
}}
[data-testid="stMain"] [data-testid*="baseButton"]:hover {{
    background: {T['accent']} !important;
    background-color: {T['accent']} !important;
    color: #FFFFFF !important;
    border-color: {T['accent']} !important;
}}
[data-testid="stMain"] [data-testid*="baseButton"]:hover p,
[data-testid="stMain"] [data-testid*="baseButton"]:hover span {{
    color: #FFFFFF !important;
}}
[data-testid="stMain"] [data-testid="baseButton-primary"] {{
    background: {T['accent']} !important;
    background-color: {T['accent']} !important;
    color: #FFFFFF !important;
    border-color: {T['accent']} !important;
}}
[data-testid="stMain"] [data-testid="baseButton-primary"] p,
[data-testid="stMain"] [data-testid="baseButton-primary"] span {{
    color: #FFFFFF !important;
    background: transparent !important;
}}

/* ══ NUCLEAR OVERRIDE — html body scope beats emotion CSS (highest !important spec) */
html body [data-testid="stMain"] button[kind="secondary"] {{
    background: {T['bg_elevated']} !important;
    background-color: {T['bg_elevated']} !important;
    color: {T['text_primary']} !important;
    border: 1px solid {T['border_strong']} !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}}
html body [data-testid="stMain"] button[kind="secondary"] p,
html body [data-testid="stMain"] button[kind="secondary"] span,
html body [data-testid="stMain"] button[kind="secondary"] div {{
    color: {T['text_primary']} !important;
    background: transparent !important;
    background-color: transparent !important;
}}
html body [data-testid="stMain"] button[kind="secondary"]:hover {{
    background: {T['accent']} !important;
    background-color: {T['accent']} !important;
    color: #FFFFFF !important;
    border-color: {T['accent']} !important;
}}
html body [data-testid="stMain"] button[kind="secondary"]:hover p,
html body [data-testid="stMain"] button[kind="secondary"]:hover span {{
    color: #FFFFFF !important;
}}
html body [data-testid="stMain"] button[kind="primary"] {{
    background: {T['accent']} !important;
    background-color: {T['accent']} !important;
    color: #FFFFFF !important;
    border-color: {T['accent']} !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
}}
html body [data-testid="stMain"] button[kind="primary"] p,
html body [data-testid="stMain"] button[kind="primary"] span,
html body [data-testid="stMain"] button[kind="primary"] div {{
    color: #FFFFFF !important;
    background: transparent !important;
    background-color: transparent !important;
}}
html body [data-testid="stMain"] button[kind="primary"]:hover {{
    filter: brightness(1.1) !important;
}}

/* ══ ELEMENT CONTAINERS — transparent to show parent background ══════════════ */
[data-testid="stMain"] .element-container,
[data-testid="stMain"] [data-testid="element-container"],
[data-testid="stMain"] .stElementContainer {{
    background: transparent !important;
    background-color: transparent !important;
}}
[data-testid="stMain"] [data-testid="stHorizontalBlock"] [data-testid="stColumn"],
[data-testid="stMain"] [data-testid="stHorizontalBlock"] [data-testid="column"] {{
    background: transparent !important;
    background-color: transparent !important;
}}

/* ══ VERTICAL BLOCK — transparent (Streamlit default is white) ═══════════════ */
[data-testid="stMain"] [data-testid="stVerticalBlock"],
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {{
    background: transparent !important;
    background-color: transparent !important;
}}
/* ══ SCROLLABLE CONTAINER (height=N) — use app bg so it looks contained ══════ */
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"]:has(> [data-testid="stVerticalBlock"]) {{
    background: {T['bg_app']} !important;
    border-radius: 10px !important;
}}

/* ══ STAPP / STMAIN — root level bg ══════════════════════════════════════════ */
.stApp > header {{ background: transparent !important; }}
[data-testid="stAppViewContainer"] {{
    background: {T['bg_app']} !important;
    background-color: {T['bg_app']} !important;
}}
[data-testid="stMain"] {{
    background: {T['bg_app']} !important;
    background-color: {T['bg_app']} !important;
}}

/* ══ TOAST / NOTIFICATION ════════════════════════════════════════════════════ */
[data-testid="stNotification"],
[data-testid="stAlert"] {{
    background: {T['bg_card']} !important;
    color: {T['text_primary']} !important;
    border-color: {T['border']} !important;
}}

/* ══ SPINNER ═════════════════════════════════════════════════════════════════ */
[data-testid="stSpinner"] > div {{
    background: {T['bg_elevated']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text_primary']} !important;
}}

/* Spinner trong SIDEBAR — phải dùng dark blue theme như sidebar (không phải light) */
[data-testid="stSidebar"] [data-testid="stSpinner"] > div,
[data-testid="stSidebar"] [data-testid="stSpinner"] {{
    background: rgba(13,71,161,0.35) !important;
    border: 1px solid rgba(191,219,254,0.25) !important;
    border-radius: 8px !important;
    color: #DBEAFE !important;
    font-size: 12px !important;
    padding: 8px 12px !important;
}}
[data-testid="stSidebar"] [data-testid="stSpinner"] div,
[data-testid="stSidebar"] [data-testid="stSpinner"] span,
[data-testid="stSidebar"] [data-testid="stSpinner"] p {{
    color: #DBEAFE !important;
    background: transparent !important;
}}
/* Spinner circle SVG */
[data-testid="stSidebar"] [data-testid="stSpinner"] svg circle {{
    stroke: #7AA4D4 !important;
}}

/* Disabled button trong sidebar — giữ dark blue, không chuyển white */
[data-testid="stSidebar"] button:disabled,
[data-testid="stSidebar"] button[disabled] {{
    background: rgba(13,71,161,0.35) !important;
    background-color: rgba(13,71,161,0.35) !important;
    color: rgba(219,234,254,0.6) !important;
    border: 1px solid rgba(191,219,254,0.20) !important;
    opacity: 1 !important;
    cursor: wait !important;
}}

/* ══ CHAT BUBBLE code block — dark mode readable ═════════════════════════════ */
.bot-msg-container code {{
    background: {'rgba(96,165,250,0.15)' if T.get('is_dark') else 'rgba(21,101,192,.08)'} !important;
    color: {T['accent']} !important;
}}
.bot-msg-container pre {{
    background: {'#0D1117' if T.get('is_dark') else '#0F172A'} !important;
    color: {'#E2E8F0' if T.get('is_dark') else '#F8FAFC'} !important;
}}

/* ══ CHAT ROW bottom border — visual separator ═══════════════════════════════ */
.chat-row + .chat-row {{
    border-top: 1px solid {T['divider']} !important;
    padding-top: 14px !important;
    margin-top: 0 !important;
}}
</style>"""



_SIDEBAR_CSS = """<style>
/* ═══════════════════════════════════════════════════════════
   SIDEBAR BACKGROUND
   ═══════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"],
div[data-testid="stSidebar"],
aside[data-testid="stSidebar"],
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1F4A 0%, #152E70 55%, #0A1838 100%) !important;
    background-color: #0D1F4A !important;
    border-right: none !important;
    box-shadow: 3px 0 16px rgba(0,0,0,0.25) !important;
}

/* ═══════════════════════════════════════════════════════════
   UNIVERSAL OVERRIDE
   ═══════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] *,
[data-testid="stSidebar"] *::before,
[data-testid="stSidebar"] *::after {
    background: transparent !important;
    background-color: transparent !important;
    background-image: none !important;
}

[data-testid="stSidebar"] * {
    color: #D0E0F5 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6,
[data-testid="stSidebar"] strong,
[data-testid="stSidebar"] b {
    color: #FFFFFF !important;
    font-weight: 800 !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] label *,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {
    color: #7AA4D4 !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}

/* ═══════════════════════════════════════════════════════════
   NAV — option_menu
   ═══════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] iframe {
    background: transparent !important;
    background-color: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stCustomComponentV1"],
[data-testid="stSidebar"] .stComponentContainer,
[data-testid="stSidebar"] .element-container:has(iframe) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}
[data-testid="stSidebar"] .nav-pills,
[data-testid="stSidebar"] ul[class*="nav"] {
    background: transparent !important;
    background-color: transparent !important;
    padding: 0 !important;
}
[data-testid="stSidebar"] ul[class*="nav"] li a,
[data-testid="stSidebar"] .nav-link {
    border-radius: 8px !important;
    transition: background .15s ease, border-color .15s ease !important;
}

/* ═══════════════════════════════════════════════════════════
   SELECTBOX
   ═══════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] [data-baseweb="select"] > div:first-child,
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,0.08) !important;
    background-color: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div:first-child *,
[data-testid="stSidebar"] .stSelectbox > div > div * {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] svg {
    color: #B8CFEE !important;
    fill: #B8CFEE !important;
}

/* ═══════════════════════════════════════════════════════════
   DROPDOWN POPUP
   ═══════════════════════════════════════════════════════════ */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] > div > div,
div[data-baseweb="popover"] > div > div > div,
div[data-baseweb="menu"],
div[data-baseweb="menu"] > ul,
div[data-baseweb="menu"] > div,
ul[role="listbox"],
div[role="listbox"],
[data-baseweb="list"],
[data-baseweb="list"] > div {
    background: #0D1F4A !important;
    background-color: #0D1F4A !important;
    border: 1px solid rgba(66,165,245,0.35) !important;
    border-radius: 10px !important;
    box-shadow: 0 8px 28px rgba(0,0,0,0.6) !important;
}
div[data-baseweb="popover"] *,
div[data-baseweb="menu"] *,
ul[role="listbox"] *,
[data-baseweb="list"] * {
    background: transparent !important;
    background-color: transparent !important;
}
div[data-baseweb="popover"] li,
div[data-baseweb="popover"] [role="option"],
ul[role="listbox"] li,
ul[role="listbox"] [role="option"],
[data-baseweb="list"] [role="option"] {
    color: #C8DEFF !important;
    font-weight: 500 !important;
    padding: 9px 14px !important;
}
div[data-baseweb="popover"] li:hover,
div[data-baseweb="popover"] [role="option"]:hover,
ul[role="listbox"] li:hover,
ul[role="listbox"] [role="option"]:hover,
[data-baseweb="list"] [role="option"]:hover {
    background: rgba(66,165,245,0.25) !important;
    background-color: rgba(66,165,245,0.25) !important;
    color: #FFFFFF !important;
}
div[data-baseweb="popover"] [aria-selected="true"],
ul[role="listbox"] [aria-selected="true"],
[data-baseweb="list"] [aria-selected="true"] {
    background: rgba(66,165,245,0.40) !important;
    background-color: rgba(66,165,245,0.40) !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
}

/* ═══════════════════════════════════════════════════════════
   DATE INPUT
   ═══════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] [data-testid="stDateInput"] label,
[data-testid="stSidebar"] .stDateInput label {
    color: rgba(191,219,254,0.75) !important;
    font-size: 9px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}
[data-testid="stSidebar"] .stDateInput > div > div,
[data-testid="stSidebar"] [data-testid="stDateInput"] > div > div,
[data-testid="stSidebar"] [data-baseweb="input"] {
    background: rgba(255,255,255,0.08) !important;
    background-color: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stDateInput input,
[data-testid="stSidebar"] input[type="text"],
[data-testid="stSidebar"] input[type="date"] {
    color: #FFFFFF !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border: none !important;
    text-align: center !important;
}
[data-baseweb="calendar"] {
    background: #152E70 !important;
    background-color: #152E70 !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
}
[data-baseweb="calendar"] * { color: #D0E0F5 !important; }
[data-baseweb="calendar"] button:hover { background: rgba(66,165,245,0.3) !important; background-color: rgba(66,165,245,0.3) !important; }
[data-baseweb="calendar"] [aria-selected="true"] { background: #42A5F5 !important; background-color: #42A5F5 !important; color: #FFFFFF !important; }

/* ═══════════════════════════════════════════════════════════
   SLIDER
   ═══════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] [data-testid="stSlider"] > div > div > div > div {
    background: #42A5F5 !important;
    background-color: #42A5F5 !important;
}
[data-testid="stSidebar"] [data-testid="stSlider"] > div > div > div {
    background: rgba(255,255,255,0.15) !important;
    background-color: rgba(255,255,255,0.15) !important;
}
[data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {
    background: #FFFFFF !important;
    background-color: #FFFFFF !important;
    border: 2px solid #42A5F5 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
}
[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBar"],
[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBar"] * {
    color: #FFFFFF !important;
    font-weight: 700 !important;
}

/* ═══════════════════════════════════════════════════════════
   BUTTONS
   ═══════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] .btn-refresh .stButton > button,
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: #1565C0 !important;
    background-color: #1565C0 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 8px rgba(21,101,192,0.4) !important;
}
[data-testid="stSidebar"] .btn-refresh .stButton > button:hover,
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: #1976D2 !important;
    background-color: #1976D2 !important;
}
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {
    background: rgba(255,255,255,0.08) !important;
    background-color: rgba(255,255,255,0.08) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]) * { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]):hover {
    background: rgba(255,255,255,0.15) !important;
    background-color: rgba(255,255,255,0.15) !important;
}

/* ═══════════════════════════════════════════════════════════
   DIVIDERS & SCROLLBAR
   ═══════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.08) !important;
    margin: 12px 0 !important;
}
[data-testid="stSidebar"]::-webkit-scrollbar { width: 6px; }
[data-testid="stSidebar"]::-webkit-scrollbar-track { background: transparent; }
[data-testid="stSidebar"]::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }
[data-testid="stSidebar"]::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.30); }

/* ═══════════════════════════════════════════════════════════
   SIDEBAR COLLAPSE / EXPAND BUTTON
   ═══════════════════════════════════════════════════════════ */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    background: #1A3A6A !important;
    background-color: #1A3A6A !important;
    border-radius: 0 12px 12px 0 !important;
    border: 1px solid rgba(112,160,220,0.4) !important;
    border-left: 3px solid #7AA4D4 !important;
    box-shadow: 4px 0 16px rgba(0,0,0,0.45) !important;
    min-width: 32px !important;
    min-height: 44px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    z-index: 100 !important;
    position: fixed !important;
    top: 12px !important;
    left: 0 !important;
    cursor: pointer !important;
}
[data-testid="collapsedControl"]:hover,
[data-testid="stSidebarCollapsedControl"]:hover {
    background: #2557A7 !important;
    background-color: #2557A7 !important;
    border-color: #D0E0F5 !important;
}
[data-testid="collapsedControl"] *,
[data-testid="collapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] *,
[data-testid="stSidebarCollapsedControl"] svg {
    color: #D0E0F5 !important;
    fill: #D0E0F5 !important;
    stroke: #D0E0F5 !important;
    background: transparent !important;
}
[data-testid="stSidebarHeader"] button,
[data-testid="stSidebarHeader"] [data-testid="baseButton-headerNoPadding"] {
    background: rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    color: #D0E0F5 !important;
}
[data-testid="stSidebarHeader"] button:hover {
    background: rgba(255,255,255,0.18) !important;
}
[data-testid="stSidebarHeader"] button svg,
[data-testid="stSidebarHeader"] button * {
    color: #D0E0F5 !important;
    fill: #D0E0F5 !important;
    background: transparent !important;
}

/* ═══════════════════════════════════════════════════════════
   MOBILE RESPONSIVE
   ═══════════════════════════════════════════════════════════ */
@media screen and (max-width: 992px) {
    .main .block-container { padding: 0.6rem 0.8rem 2rem !important; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 0.5rem !important; }
}

@media screen and (max-width: 768px) {
    .main .block-container {
        padding: 0.5rem 0.5rem 1.5rem !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 0.4rem !important; }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        min-width: calc(50% - 0.4rem) !important;
        flex: 1 1 calc(50% - 0.4rem) !important;
        box-sizing: border-box !important;
    }
    .main * { word-break: break-word !important; overflow-wrap: break-word !important; }
    .stDataFrame, .stTable, .hist-tbl-wrap {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }
    .stPlotlyChart { width: 100% !important; touch-action: pan-y !important; }
    [data-testid="stMetricValue"] { font-size: clamp(16px, 4vw, 22px) !important; }
    [data-testid="stMetricLabel"] { font-size: clamp(9px, 2vw, 11px) !important; }
    .stTabs [data-baseweb="tab"] { padding: 12px 16px !important; min-height: 44px !important; }
    .main .stButton > button,
    .main .stDownloadButton > button { min-height: 44px !important; padding: 10px 16px !important; }
    .page-header h1 { font-size: 16px !important; }
    .page-header p  { font-size: 10.5px !important; }
    .sec-hdr { font-size: 10px !important; padding: 5px 10px !important; letter-spacing: 0.8px !important; }
    .alert-card { padding: 12px 14px !important; font-size: 12px !important; }
}

@media screen and (max-width: 480px) {
    .main .block-container { padding: 0.35rem 0.35rem 1rem !important; }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
        margin-bottom: 0.4rem !important;
    }
    .main { font-size: 12px !important; }
    .sec-hdr { font-size: 9.5px !important; padding: 4px 8px !important; letter-spacing: 0.5px !important; }
    .page-header { padding: 10px 14px !important; }
    .page-header h1 { font-size: 15px !important; }
    .page-header p  { font-size: 10px !important; }
    [data-testid="stMetricValue"] { font-size: 16px !important; }
    .stTabs [data-baseweb="tab"] { padding: 10px 12px !important; font-size: 12px !important; }
    .hist-tbl th, .hist-tbl td { padding: 5px 7px !important; font-size: 11px !important; }
    .main [data-testid="stHorizontalBlock"] .stButton > button {
        padding: 6px 10px !important; font-size: 11px !important; min-height: 40px !important;
    }
}

@media screen and (max-width: 360px) {
    .main .block-container { padding: 0.25rem 0.25rem 0.8rem !important; }
    .main { font-size: 11px !important; }
    .page-header h1 { font-size: 14px !important; }
    [data-testid="stMetricValue"] { font-size: 14px !important; }
}

@media (hover: none) and (pointer: coarse) {
    button, [role="button"], .stButton > button, .stDownloadButton > button,
    .stTabs [data-baseweb="tab"] { min-height: 44px !important; }
    .fc-card:hover { transform: none !important; }
}

/* ═══════════════════════════════════════════════════════════
   SIDEBAR LUÔN HIỆN
   ═══════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    display: block !important;
    visibility: visible !important;
    transform: translateX(0) !important;
    margin-left: 0 !important;
    min-width: 280px !important;
    width: 280px !important;
    max-width: 280px !important;
    position: relative !important;
    left: 0 !important;
    opacity: 1 !important;
}

[data-testid="stSidebarHeader"],
[data-testid="stSidebarCollapseButton"],
button[data-testid="baseButton-headerNoPadding"] {
    display: none !important;
}

[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

@media screen and (max-width: 768px) {
    [data-testid="stSidebar"] {
        min-width: 200px !important;
        width: 200px !important;
        max-width: 200px !important;
        position: relative !important;
        transform: translateX(0) !important;
    }
    .main .block-container {
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
    }
}
@media screen and (max-width: 480px) {
    [data-testid="stSidebar"] {
        min-width: 180px !important;
        width: 180px !important;
        max-width: 180px !important;
    }
}

/* ═══════════════════════════════════════════════════════════
   SIDEBAR NUMBER INPUT — SCOPE HẸP, không đụng select/date
   ═══════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] > div {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.10) !important;
    border-radius: 10px !important;
    padding: 0 !important;
    overflow: hidden !important;
}
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] > div:focus-within {
    border-color: #7AA4D4 !important;
    background: rgba(122, 164, 212, 0.10) !important;
}
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input[type="number"] {
    background: transparent !important;
    border: none !important;
    color: #FFFFFF !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    text-align: center !important;
    padding: 12px 8px !important;
    cursor: text !important;
    caret-color: #7AA4D4 !important;
}
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input[type="number"]::-webkit-inner-spin-button,
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input[type="number"]::-webkit-outer-spin-button {
    -webkit-appearance: none !important;
    margin: 0 !important;
}
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] button {
    background: rgba(255, 255, 255, 0.04) !important;
    border: none !important;
    border-left: 1px solid rgba(255, 255, 255, 0.08) !important;
    color: rgba(191, 219, 254, 0.8) !important;
    width: 36px !important;
    min-width: 36px !important;
}
section[data-testid="stSidebar"] div[data-testid="stNumberInput"] button:hover {
    background: rgba(122, 164, 212, 0.25) !important;
    color: #FFFFFF !important;
}

/* ═══════════════════════════════════════════════════════════
   SIDEBAR SELECTBOX — FORCE màu rõ ràng, không cho CSS khác đè
   ═══════════════════════════════════════════════════════════ */

/* Container selectbox */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div {
    background: rgba(255, 255, 255, 0.08) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 10px !important;
    color: #FFFFFF !important;
}

section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div:hover {
    border-color: rgba(122, 164, 212, 0.5) !important;
    background: rgba(255, 255, 255, 0.12) !important;
}

/* Text hiển thị giá trị đã chọn (ví dụ "FPT") */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background: transparent !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    font-size: 14px !important;
}

/* Input bên trong */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] input {
    color: #FFFFFF !important;
    font-weight: 700 !important;
}

/* Single value container */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [class*="singleValue"],
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [class*="SingleValue"] {
    color: #FFFFFF !important;
}

/* Icon dropdown (mũi tên xuống) */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] svg {
    fill: rgba(191, 219, 254, 0.8) !important;
}

/* Dropdown menu popup */
div[data-baseweb="popover"] [role="listbox"] {
    background: #0F1729 !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
}

div[data-baseweb="popover"] [role="option"] {
    background: transparent !important;
    color: #FFFFFF !important;
}

div[data-baseweb="popover"] [role="option"]:hover {
    background: rgba(122, 164, 212, 0.25) !important;
}

/* Placeholder khi chưa chọn */
section[data-testid="stSidebar"] div[data-testid="stSelectbox"] [class*="placeholder"] {
    color: rgba(191, 219, 254, 0.5) !important;
}
</style>
<script></script>"""


_GLOBAL_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="st-"] { font-family: 'Inter','Segoe UI',system-ui,sans-serif !important; }

/* Desktop: constrain max-width để không bị stretch xấu trên 4K/ultrawide.
   Auto center với margin:auto. Mobile media-query bên dưới override khi cần. */
.main .block-container {
    padding: 1rem 2rem 3rem;
    max-width: 1600px;
    margin: 0 auto;
}
[data-testid="stSidebar"] > div { padding-top: 0.4rem; }

[data-testid="stMetric"] {
  border-radius: 12px !important;
  padding: 14px 16px !important;
}
[data-testid="stMetricLabel"] p {
  font-size: 10px !important; font-weight: 700 !important;
  letter-spacing: .6px !important; text-transform: uppercase !important;
}
[data-testid="stMetricValue"] { font-size: 18px !important; font-weight: 800 !important; }
[data-testid="stMetricDelta"] { font-size: 11.5px !important; font-weight: 600 !important; }

.page-header {
  border-radius: 14px; padding: 14px 24px 12px; margin-bottom: 16px;
  position: relative; overflow: hidden;
}
.page-header h1 { font-size: 18px; margin: 0 0 3px; font-weight: 800; letter-spacing: -.3px; }
.page-header p  { margin: 0; font-size: 11.5px; font-weight: 500; }

.alert-card {
  border-radius: 12px; padding: 14px 18px; margin: 8px 0;
  border-left: 5px solid; font-size: 13px; line-height: 1.6;
}
.alert-buy  { background: #E8F5E9; border-color: #2E7D32; color: #1B4D20; }
.alert-sell { background: #FFEBEE; border-color: #C62828; color: #7A1515; }
.alert-warn { background: #FFF8E1; border-color: #F9A825; color: #6D4C00; }
.alert-neut { background: #F3F6FA; border-color: #8090B0; color: #3A4A6A; }

.info-box {
  border-radius: 10px; padding: 10px 16px;
  font-size: 13px; margin: 8px 0; line-height: 1.7;
}

.fc-card {
  border-radius: 14px; padding: 20px 16px 15px;
  text-align: center; transition: transform .18s, box-shadow .18s;
  position: relative; overflow: hidden;
}
.fc-card:hover { transform: translateY(-3px); }
.fc-method { font-size: 9px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; }
.up   { color: #166534; background: #DCFCE7; }
.down { color: #991B1B; background: #FEE2E2; }
.flat { color: #475569; background: #F1F5F9; }

[data-testid="stIconMaterial"] { display: none !important; }
.material-symbols-outlined, .material-symbols-rounded,
[class*="material-symbols"] { font-size: 0 !important; }
button span[translate="no"],
[data-testid="stDownloadButton"] span[translate="no"],
[data-testid="stButton"] span[translate="no"] {
    font-size: inherit !important;
    line-height: inherit !important;
}

[data-testid="stAlert"] { border-radius: 10px !important; font-size: 13px !important; }
details > summary { font-size: 13px !important; font-weight: 600 !important; }
#MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }

/* ═══════════════════════════════════════════════════════════════
   CHATBOT — Premium redesigned UI
   ═══════════════════════════════════════════════════════════════ */

/* Status banner */
.chat-status {
    display: flex; align-items: center; gap: 8px;
    padding: 9px 14px; margin: 8px 0 12px;
    font-size: 11.5px; font-weight: 600;
    border-radius: 8px; border: 1px solid;
}
.chat-status-ok {
    background: linear-gradient(90deg,rgba(16,185,129,.10) 0%,rgba(16,185,129,0) 100%);
    border-color: rgba(16,185,129,.30); color: #047857;
}
.chat-status-warn {
    background: linear-gradient(90deg,rgba(245,158,11,.10) 0%,rgba(245,158,11,0) 100%);
    border-color: rgba(245,158,11,.30); color: #92400E;
}

/* Chat rows */
.chat-row {
    display: flex; gap: 12px; padding: 10px 6px; margin: 4px 0;
    border-radius: 10px; animation: chatFadeIn .28s ease-out;
    transition: background .15s;
}
.chat-row:hover { background: rgba(100,116,139,.04); }
@keyframes chatFadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.chat-row.chat-user { flex-direction: row-reverse; }
.chat-row.chat-bot  { flex-direction: row; }

/* Avatar */
.chat-avatar {
    width: 34px; height: 34px; min-width: 34px;
    border-radius: 50%;
    background: linear-gradient(135deg,#1565C0 0%,#7C3AED 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 10px; font-weight: 800; color: white; letter-spacing: .5px;
    box-shadow: 0 2px 10px rgba(21,101,192,.40);
    flex-shrink: 0; margin-top: 2px;
}
.chat-row.chat-user .chat-avatar {
    background: linear-gradient(135deg,#334155 0%,#475569 100%);
    box-shadow: 0 2px 8px rgba(0,0,0,.20);
}

.chat-bubble-wrap {
    display: flex; flex-direction: column; max-width: 78%; min-width: 0;
}
.chat-row.chat-user .chat-bubble-wrap { align-items: flex-end; }
.chat-row.chat-bot  .chat-bubble-wrap { align-items: flex-start; flex: 1; }

/* Meta row */
.chat-meta {
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 4px; font-size: 9.5px;
}
.chat-label {
    font-weight: 800; letter-spacing: 1.2px;
    text-transform: uppercase; color: #64748B;
}
.chat-time  { color: #94A3B8; font-weight: 500; font-family: monospace; font-size: 9px; }

/* Bubble */
.chat-bubble {
    padding: 11px 15px; font-size: 13.5px; line-height: 1.68;
    word-wrap: break-word; word-break: break-word;
    transition: box-shadow .18s;
}
.chat-bubble-user {
    color: white; font-weight: 500;
    border-radius: 16px 16px 4px 16px;
    box-shadow: 0 3px 12px rgba(21,101,192,.28);
}
.chat-bubble-bot {
    border-radius: 4px 16px 16px 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.chat-bubble-bot:hover { box-shadow: 0 3px 10px rgba(0,0,0,.10); }

/* Bot markdown content */
.bot-msg-container h1,.bot-msg-container h2,.bot-msg-container h3,.bot-msg-container h4 {
    font-weight: 700 !important; color: inherit !important;
    border-bottom: 1px solid rgba(100,116,139,.15);
    padding-bottom: 4px !important; margin-bottom: 8px !important;
}
.bot-msg-container h1 { font-size: 17px !important; margin-top: 14px !important; }
.bot-msg-container h2 { font-size: 15.5px !important; margin-top: 12px !important; }
.bot-msg-container h3 { font-size: 14.5px !important; margin-top: 10px !important; }
.bot-msg-container h4 { font-size: 13.5px !important; margin-top: 8px !important; border: none !important; }
.bot-msg-container p  { margin: 5px 0 !important; line-height: 1.72 !important; }
.bot-msg-container ul { margin: 5px 0 5px 18px !important; list-style: disc !important; }
.bot-msg-container ol { margin: 5px 0 5px 18px !important; }
.bot-msg-container li { margin: 4px 0 !important; line-height: 1.6 !important; }
.bot-msg-container code {
    padding: 2px 6px !important; border-radius: 4px !important;
    font-family: 'Menlo','Consolas',monospace !important; font-size: 12px !important;
    font-weight: 600 !important;
}
.bot-msg-container pre {
    padding: 12px 14px !important; border-radius: 8px !important;
    overflow-x: auto !important; margin: 8px 0 !important;
    font-size: 12px !important; line-height: 1.5 !important;
}
.bot-msg-container pre code {
    background: transparent !important;
    color: inherit !important;
    padding: 0 !important;
    font-size: 12px !important;
}
.bot-msg-container table {
    border-collapse: collapse !important; width: 100% !important;
    margin: 10px 0 !important; font-size: 12.5px !important;
    border-radius: 6px !important; overflow: hidden !important;
}
.bot-msg-container th, .bot-msg-container td {
    border: 1px solid rgba(100,116,139,.2) !important;
    padding: 7px 11px !important; text-align: left !important;
}
.bot-msg-container th {
    background: rgba(21,101,192,.08) !important;
    font-weight: 700 !important; font-size: 11.5px !important;
    text-transform: uppercase !important; letter-spacing: .4px !important;
}
.bot-msg-container blockquote {
    border-left: 3px solid #F59E0B !important; padding: 7px 13px !important;
    margin: 8px 0 !important; background: rgba(245,158,11,.06) !important;
    border-radius: 0 8px 8px 0 !important; font-size: 12.5px !important;
    font-style: italic !important;
}
.bot-msg-container hr {
    border: none !important; border-top: 1px solid rgba(100,116,139,.2) !important;
    margin: 10px 0 !important;
}
.bot-msg-container strong { font-weight: 700 !important; }
.bot-msg-container em { font-style: italic !important; }

/* Suggestion chip special — pill shape */
.sug-chip button {
    border-radius: 20px !important;
    font-size: 12px !important;
    padding: 5px 12px !important;
    min-height: 34px !important;
    font-weight: 500 !important;
}

/* Typing dots */
.typing-dots { display: inline-flex; gap: 5px; padding: 10px 14px; }
.typing-dots span {
    width: 7px; height: 7px; border-radius: 50%; background: #94A3B8;
    animation: typingBounce 1.4s infinite;
}
.typing-dots span:nth-child(2) { animation-delay: .18s; }
.typing-dots span:nth-child(3) { animation-delay: .36s; }
@keyframes typingBounce {
    0%, 60%, 100% { transform: translateY(0); opacity: .35; }
    30%            { transform: translateY(-7px); opacity: 1; }
}

/* ═══════════════════════════════════════════════════════════════
   CHATBOT — Chat input
   ═══════════════════════════════════════════════════════════════ */

div[data-testid="stChatInput"] { margin-top: 10px !important; }
div[data-testid="stChatInput"] > div {
    border-radius: 14px !important;
    box-shadow: 0 2px 12px rgba(21,101,192,.10) !important;
    transition: box-shadow .2s !important;
}
div[data-testid="stChatInput"] > div:focus-within {
    box-shadow: 0 4px 20px rgba(21,101,192,.22) !important;
}

/* ── Conversation history scrollable container ── */
/* Icon buttons (✏ ✕) inside the fixed-height scroll box */
div[data-testid="stVerticalBlockBorderWrapper"]
    .main [data-testid="stColumn"] .stButton > button {
    padding: 5px 8px !important;
    min-height: 32px !important;
    font-size: 12px !important;
    border-radius: 8px !important;
}
/* Title button (conversation name) — left-ish feel */
div[data-testid="stVerticalBlockBorderWrapper"]
    .main [data-testid="stColumn"]:first-child .stButton > button {
    padding: 6px 10px !important;
    min-height: 34px !important;
    font-size: 12.5px !important;
    border-radius: 8px !important;
    text-overflow: ellipsis !important;
    overflow: hidden !important;
    white-space: nowrap !important;
}

/* Smooth scroll */
html { scroll-behavior: smooth; }

/* ══ VERTICAL BLOCK — base transparent (overridden by theme CSS) ════════════ */
[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"] {
    background: transparent !important;
    background-color: transparent !important;
}

/* ══ POPOVER MENU from main area ════════════════════════════════════════════ */
[data-testid="stPopover"] [data-testid="stVerticalBlock"] {
    background: var(--bg-card, #FFFFFF) !important;
}

</style>"""


def inject_global_css() -> None:
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def inject_theme_css(T: dict) -> None:
    st.markdown(_theme_css(T), unsafe_allow_html=True)
    st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)
