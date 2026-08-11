"""
streamlit_app.py
-----------------
AuditLens dashboard -- Dark mode analytics deliverable. 
Matches the requested visual layout: dark background, red filter tags, 
and light blue area charts. Fixed sidebar and multiselect placeholder visibility.

Run with:
    pip install streamlit plotly
    streamlit run dashboard/streamlit_app.py
"""

import os
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ---------------------------------------------------------------------------
# CONFIG & PATHS
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "dashboard_export.csv")

st.set_page_config(
    page_title="AuditLens | Audit Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# COLOR SYSTEM
# ---------------------------------------------------------------------------

COLORS = {
    "bg": "#0E1117",
    "sidebar": "#262730",
    "text": "#FAFAFA",
    "muted": "#A0A6B1",
    "chart_blue": "#76B3F0", 
    "chart_blue_fill": "rgba(118, 179, 240, 0.3)",
    "tag_red": "#E04C4C",
    "grid": "#2B2B36",
    "low": "#1FA97A",
    "medium": "#E8A33D",
    "high": "#E0483C",
}

RISK_COLOR_MAP = {
    "Low": COLORS["low"],
    "Medium": COLORS["medium"],
    "High": COLORS["high"],
}

RISK_ORDER = ["Low", "Medium", "High"]


# ---------------------------------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------------------------------

st.markdown(
    f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, Helvetica, Arial, sans-serif;
        color: {COLORS['text']};
    }}

    .stApp {{
        background-color: {COLORS['bg']};
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{background: transparent !important;}}

    .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
        max-width: 100%;
    }}

    /* --- Headers --- */
    h1, h2, h3, .section-title {{
        color: {COLORS['text']} !important;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
    }}
    
    .section-title {{
        font-size: 22px;
        margin: 24px 0 16px 0;
    }}

    /* --- KPI cards --- */
    div[data-testid="stMetric"] {{
        background: transparent;
        border: none;
        padding: 8px 0px;
    }}

    div[data-testid="stMetric"] label {{
        font-size: 13px !important;
        font-weight: 500 !important;
        color: {COLORS['text']} !important;
    }}

    div[data-testid="stMetricValue"] {{
        font-family: 'Inter', sans-serif !important;
        font-size: 34px !important;
        font-weight: 700 !important;
        color: {COLORS['text']} !important;
    }}

    div[data-testid="stMetricDelta"] {{
        font-size: 12px !important;
    }}

    /* --- Sidebar Visibility Fix --- */
    section[data-testid="stSidebar"] {{
        background-color: {COLORS['sidebar']} !important;
        border-right: 1px solid {COLORS['grid']} !important;
    }}

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label {{
        color: {COLORS['text']} !important;
    }}

    /* Specific fix for slider text */
    .stSlider [data-testid="stTickBar"] *,
    .stSlider [data-testid="stThumbValue"] {{
        color: {COLORS['text']} !important;
    }}

    section[data-testid="stSidebar"] hr {{
        border-color: {COLORS['grid']} !important;
    }}

    /* --- Multiselect Visibility Fix --- */
    /* Make placeholder and icons dark against white background */
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] input,
    div[data-baseweb="select"] svg {{
        color: #1E1E1E !important;
        fill: #1E1E1E !important;
    }}
    
    /* Multiselect Tags (Red background, White text) */
    .stMultiSelect [data-baseweb="tag"] {{
        background-color: {COLORS['tag_red']} !important;
        color: white !important;
        border-radius: 4px;
        border: none !important;
    }}
    
    .stMultiSelect [data-baseweb="tag"] span,
    .stMultiSelect [data-baseweb="tag"] svg {{
        color: white !important;
        fill: white !important;
    }}

    /* --- Dataframe --- */
    div[data-testid="stDataFrame"] {{
        border: 1px solid {COLORS['grid']};
        border-radius: 4px;
    }}

    /* --- Tabs Visibility Fix --- */
    button[data-baseweb="tab"] p {{
        color: {COLORS['muted']} !important;
        font-weight: 600;
        font-size: 15px;
    }}
    
    button[data-baseweb="tab"]:hover p {{
        color: {COLORS['text']} !important;
    }}
    
    button[data-baseweb="tab"][aria-selected="true"] p {{
        color: {COLORS['tag_red']} !important;
    }}
    
    div[data-baseweb="tab-highlight"] {{
        background-color: {COLORS['tag_red']} !important;
    }}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

@st.cache_data
def load_data(path):
    df = pd.read_csv(path, parse_dates=["date"])
    df["risk_level"] = pd.Categorical(
        df["risk_level"],
        categories=RISK_ORDER,
        ordered=True,
    )
    return df


if not os.path.exists(DATA_PATH):
    st.title("AuditLens Dashboard")
    st.error(
        "Run `auditlens_walkthrough.ipynb` first to generate "
        "data/dashboard_export.csv."
    )
    st.stop()


df = load_data(DATA_PATH)

df["vendor_frequency"] = df["vendor"].map(
    df["vendor"].value_counts()
)


# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------

st.title("AuditLens Dashboard")


# ---------------------------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Filters")
    st.markdown("---")

    dept_filter = st.multiselect(
        "Department",
        sorted(df["department"].unique()),
        placeholder="Choose an option",
    )

    risk_filter = st.multiselect(
        "Risk Level",
        RISK_ORDER,
        default=["Medium", "High"],
    )

    month_range = st.slider(
        "Month range",
        1,
        12,
        (1, 12),
    )

    st.markdown("---")

    st.markdown(
        f"""
        <span style='font-size:12px; color:{COLORS["text"]} !important;'>
            Showing data filtered to the selections above.<br><br>
            Full dataset: {len(df):,} transactions.
        </span>
        """,
        unsafe_allow_html=True,
    )


filtered = df.copy()

if dept_filter:
    filtered = filtered[
        filtered["department"].isin(dept_filter)
    ]

if risk_filter:
    filtered = filtered[
        filtered["risk_level"].isin(risk_filter)
    ]

filtered = filtered[
    (filtered["month"] >= month_range[0])
    & (filtered["month"] <= month_range[1])
]


# ---------------------------------------------------------------------------
# PLOTLY LAYOUT
# ---------------------------------------------------------------------------

PLOTLY_LAYOUT: dict[str, Any] = dict(
    font=dict(
        family="Inter, sans-serif",
        color=COLORS["muted"],
        size=11,
    ),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(
        l=10,
        r=10,
        t=30,
        b=10,
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=11, color=COLORS["text"]),
    )
)


# ---------------------------------------------------------------------------
# EXECUTIVE SUMMARY / KPI METRICS
# ---------------------------------------------------------------------------

st.markdown('<div class="section-title">KPI Metrics</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Total Transactions", f"{len(df):,}")
c2.metric("Total Value", f"₹{df['amount'].sum() / 1e6:,.2f}M")
c3.metric(
    "High Risk Count",
    f"{(df['risk_level'] == 'High').sum():,}"
)
c4.metric(
    "Medium Risk Count",
    f"{(df['risk_level'] == 'Medium').sum():,}"
)
c5.metric("Unique Vendors", f"{df['vendor'].nunique():,}")

st.markdown("<br>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------

tab1, tab2, tab3 = st.tabs(
    [
        "Overview",
        "Vendor Risk",
        "Transaction Detail",
    ]
)


# ---------------------------------------------------------------------------
# TAB 1: OVERVIEW
# ---------------------------------------------------------------------------

with tab1:

    st.markdown('<div class="section-title">Transactions Over Time</div>', unsafe_allow_html=True)

    monthly = df.groupby("month")["amount"].sum().reset_index()

    fig_line = go.Figure()
    fig_line.add_trace(
        go.Scatter(
            x=monthly["month"],
            y=monthly["amount"],
            mode="lines",
            line=dict(color=COLORS["chart_blue"], width=2),
            fill="tozeroy",
            fillcolor=COLORS["chart_blue_fill"],
        )
    )

    fig_line.update_layout(
        **PLOTLY_LAYOUT,
        height=350,
        xaxis=dict(
            title="Month", 
            gridcolor=COLORS["grid"], 
            zerolinecolor=COLORS["grid"],
            dtick=1
        ),
        yaxis=dict(
            title="Total Value (₹)",
            gridcolor=COLORS["grid"],
            zerolinecolor=COLORS["grid"],
            tickformat=",.0f",
        ),
    )

    st.plotly_chart(fig_line, width="stretch", use_container_width=True)
    
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown('<div class="section-title">Risk Level Distribution</div>', unsafe_allow_html=True)

        risk_counts = (
            df["risk_level"]
            .value_counts()
            .reindex(RISK_ORDER)
            .reset_index()
        )
        risk_counts.columns = ["risk_level", "count"]

        fig_donut = go.Figure(
            data=[
                go.Pie(
                    labels=risk_counts["risk_level"],
                    values=risk_counts["count"],
                    hole=0.7,
                    marker=dict(
                        colors=[
                            RISK_COLOR_MAP[r]
                            for r in risk_counts["risk_level"]
                        ],
                        line=dict(color=COLORS["bg"], width=2),
                    ),
                    textinfo="percent",
                    textfont=dict(size=12, color="white", family="Inter"),
                )
            ]
        )

        fig_donut.update_layout(
            **PLOTLY_LAYOUT,
            height=300,
        )

        st.plotly_chart(fig_donut, width="stretch", use_container_width=True)

    with col_right:
        st.markdown('<div class="section-title">Rule Tests Triggered</div>', unsafe_allow_html=True)

        test_counts = (
            df[df["tests_triggered"].notna() & (df["tests_triggered"] != "")][
                "tests_triggered"
            ]
            .str.split(", ")
            .explode()
            .value_counts()
            .sort_values(ascending=True)
        )

        fig_tests = go.Figure(
            go.Bar(
                x=test_counts.values,
                y=[t.replace("_", " ").title() for t in test_counts.index],
                orientation="h",
                marker=dict(color=COLORS["chart_blue"]),
            )
        )

        fig_tests.update_layout(
            **PLOTLY_LAYOUT,
            height=300,
            xaxis=dict(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"]),
            yaxis=dict(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"]),
        )

        st.plotly_chart(fig_tests, width="stretch", use_container_width=True)


# ---------------------------------------------------------------------------
# TAB 2: VENDOR RISK
# ---------------------------------------------------------------------------

with tab2:

    st.markdown('<div class="section-title">Top 10 Vendors by Flagged Value</div>', unsafe_allow_html=True)

    vendor_risk = (
        df[df["risk_level"].isin(["High", "Medium"])]
        .groupby("vendor")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )

    fig_vendor = go.Figure(
        go.Bar(
            x=vendor_risk["vendor"],
            y=vendor_risk["amount"],
            marker=dict(color=COLORS["chart_blue"]),
        )
    )

    fig_vendor.update_layout(
        **PLOTLY_LAYOUT,
        height=380,
        xaxis=dict(title="", tickangle=-45, gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"]),
        yaxis=dict(
            title="Flagged Value (₹)",
            tickformat=",.0f",
            gridcolor=COLORS["grid"], 
            zerolinecolor=COLORS["grid"],
        ),
    )

    st.plotly_chart(fig_vendor, width="stretch", use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="section-title">Vendor Frequency vs. Amount</div>', unsafe_allow_html=True)

        fig_scatter = go.Figure()
        for level in RISK_ORDER:
            subset = df[df["risk_level"] == level]
            fig_scatter.add_trace(
                go.Scatter(
                    x=subset["vendor_frequency"],
                    y=subset["amount"],
                    mode="markers",
                    name=level,
                    marker=dict(
                        size=6,
                        color=RISK_COLOR_MAP[level],
                        opacity=0.8,
                    ),
                )
            )

        fig_scatter.update_layout(
            **PLOTLY_LAYOUT,
            height=340,
            xaxis=dict(title="Vendor Transaction Frequency", gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"]),
            yaxis=dict(title="Amount (₹)", gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"]),
        )

        st.plotly_chart(fig_scatter, width="stretch", use_container_width=True)

    with col_b:
        st.markdown('<div class="section-title">Spend Share by Department</div>', unsafe_allow_html=True)

        dept_spend = (
            df.groupby("department")["amount"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )

        fig_dept = go.Figure(
            go.Bar(
                x=dept_spend["department"],
                y=dept_spend["amount"],
                marker=dict(color=COLORS["chart_blue"]),
            )
        )

        fig_dept.update_layout(
            **PLOTLY_LAYOUT,
            height=340,
            xaxis=dict(title="", tickangle=-20, gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"]),
            yaxis=dict(
                title="Total Spend (₹)",
                tickformat=",.0f",
                gridcolor=COLORS["grid"], 
                zerolinecolor=COLORS["grid"]
            ),
        )

        st.plotly_chart(fig_dept, width="stretch", use_container_width=True)


# ---------------------------------------------------------------------------
# TAB 3: TRANSACTION DETAIL
# ---------------------------------------------------------------------------

with tab3:

    st.markdown('<div class="section-title">Flagged Transactions (filtered)</div>', unsafe_allow_html=True)

    flagged = filtered[
        filtered["risk_level"].isin(["High", "Medium"])
    ].sort_values("risk_score", ascending=False)

    display_cols = [
        "transaction_id",
        "date",
        "vendor",
        "account",
        "amount",
        "risk_score",
        "risk_level",
        "reasons",
    ]

    st.markdown(
        f"""
        <span style='color:{COLORS["muted"]}; font-size:13px;'>
            {len(flagged):,} transactions match the current filters
        </span>
        """,
        unsafe_allow_html=True,
    )

    st.dataframe(
        flagged[display_cols]
        .style.format(
            {
                "amount": "₹{:,.2f}",
                "risk_score": "{:.3f}",
                "date": "{:%Y-%m-%d}",
            }
        )
        .map(
            lambda v: (
                f"color: {RISK_COLOR_MAP.get(str(v), COLORS['text'])}; "
                "font-weight:700;"
            ),
            subset=["risk_level"],
        ),
        width="stretch",
        height=480,
        hide_index=True,
    )