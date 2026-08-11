"""
streamlit_app.py
-----------------
AuditLens dashboard -- a code-based alternative to Power BI, styled to look
like a real audit analytics deliverable rather than a default Streamlit app.

Run with:
    pip install streamlit plotly
    streamlit run dashboard/streamlit_app.py

Reads data/dashboard_export.csv, produced by auditlens_walkthrough.ipynb
(the end-to-end pipeline notebook).
"""

import os
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ---------------------------------------------------------------------------
# CONFIG & PATHS
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "dashboard_export.csv")

st.set_page_config(
    page_title="AuditLens | Audit Analytics",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# COLOR SYSTEM -- used consistently across CSS + every chart below
# ---------------------------------------------------------------------------

COLORS = {
    "navy": "#0B1F3A",
    "navy_light": "#13284A",
    "slate": "#5A6B87",
    "bg": "#F4F6FA",
    "card": "#FFFFFF",
    "border": "#E4E8F0",
    "accent": "#2C5CE0",
    "low": "#1FA97A",
    "medium": "#E8A33D",
    "high": "#E0483C",
    "text": "#1A2438",
    "text_muted": "#7C8AA5",
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, sans-serif;
    }}

    .stApp {{
        background-color: {COLORS['bg']};
    }}

    /* Hide default Streamlit chrome */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }}

    /* --- Header banner --- */
    .app-header {{
        background: linear-gradient(
            120deg,
            {COLORS['navy']} 0%,
            {COLORS['navy_light']} 100%
        );
        border-radius: 14px;
        padding: 28px 32px;
        margin-bottom: 28px;
        color: white;
    }}

    .app-header h1 {{
        font-size: 26px;
        font-weight: 800;
        margin: 0 0 4px 0;
        letter-spacing: -0.3px;
        color: white;
    }}

    .app-header p {{
        font-size: 14px;
        color: #B9C4DA;
        margin: 0;
        font-weight: 400;
    }}

    .app-header .badge {{
        display: inline-block;
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.4px;
        text-transform: uppercase;
        margin-top: 10px;
        color: #D6DEEF;
    }}

    /* --- Section headers --- */
    .section-title {{
        font-size: 15px;
        font-weight: 700;
        color: {COLORS['text']};
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin: 6px 0 14px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid {COLORS['border']};
    }}

    /* --- KPI cards --- */
    div[data-testid="stMetric"] {{
        background: {COLORS['card']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 18px 20px 14px 20px;
        box-shadow: 0 1px 3px rgba(11,31,58,0.04);
    }}

    div[data-testid="stMetric"] label {{
        font-size: 12px !important;
        font-weight: 600 !important;
        color: {COLORS['text_muted']} !important;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }}

    div[data-testid="stMetricValue"] {{
        font-size: 26px !important;
        font-weight: 800 !important;
        color: {COLORS['navy']} !important;
    }}

    /* --- Chart containers --- */
    div[data-testid="stPlotlyChart"] {{
        background: {COLORS['card']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 14px;
        box-shadow: 0 1px 3px rgba(11,31,58,0.04);
    }}

    /* --- Sidebar --- */
    section[data-testid="stSidebar"] {{
        background-color: {COLORS['navy']};
    }}

    section[data-testid="stSidebar"] * {{
        color: #E4E9F5 !important;
    }}

    section[data-testid="stSidebar"] .stMultiSelect label,
    section[data-testid="stSidebar"] .stSlider label {{
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        color: #9FB0D0 !important;
    }}

    /* --- Dataframe --- */
    div[data-testid="stDataFrame"] {{
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        overflow: hidden;
    }}

    /* --- Tabs --- */
    button[data-baseweb="tab"] {{
        font-weight: 600;
        font-size: 14px;
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
    st.markdown(
        '<div class="app-header"><h1>AuditLens</h1>'
        '<p>data/dashboard_export.csv not found.</p></div>',
        unsafe_allow_html=True,
    )
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

st.markdown(
    f"""
<div class="app-header">
    <h1>🔍 AuditLens</h1>
    <p>
        Automated Audit Analytics &amp; Anomaly Detection
        &mdash; Journal Entry Risk Review
    </p>
    <span class="badge">
        {df['date'].min().strftime('%b %Y')}
        &ndash;
        {df['date'].max().strftime('%b %Y')}
    </span>
</div>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Filters")
    st.markdown("---")

    dept_filter = st.multiselect(
        "Department",
        sorted(df["department"].unique()),
        placeholder="All departments",
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
        <span style='font-size:12px; color:#9FB0D0;'>
            Showing data filtered to the selections above.
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
        color=COLORS["text"],
        size=12,
    ),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(
        l=10,
        r=10,
        t=10,
        b=10,
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
)


# ---------------------------------------------------------------------------
# EXECUTIVE SUMMARY
# Always on full dataset, not filtered -- true totals
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="section-title">Executive Summary</div>',
    unsafe_allow_html=True,
)

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Total Transactions",
    f"{len(df):,}",
)

c2.metric(
    "Total Value",
    f"₹{df['amount'].sum() / 1e6:,.1f}M",
)

c3.metric(
    "High Risk",
    f"{(df['risk_level'] == 'High').sum():,}",
    f"{(df['risk_level'] == 'High').mean() * 100:.1f}% of total",
)

c4.metric(
    "Medium Risk",
    f"{(df['risk_level'] == 'Medium').sum():,}",
    f"{(df['risk_level'] == 'Medium').mean() * 100:.1f}% of total",
)

c5.metric(
    "Distinct Vendors",
    f"{df['vendor'].nunique():,}",
)

st.markdown("<br>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------

tab1, tab2, tab3 = st.tabs(
    [
        "📊  Overview",
        "🏢  Vendor Risk",
        "📋  Transaction Detail",
    ]
)


# ---------------------------------------------------------------------------
# TAB 1: OVERVIEW
# ---------------------------------------------------------------------------

with tab1:

    col_left, col_right = st.columns([1, 1.4])

    # -----------------------------------------------------------------------
    # Risk Level Distribution
    # -----------------------------------------------------------------------

    with col_left:

        st.markdown(
            '<div class="section-title">Risk Level Distribution</div>',
            unsafe_allow_html=True,
        )

        risk_counts = (
            df["risk_level"]
            .value_counts()
            .reindex(RISK_ORDER)
            .reset_index()
        )

        risk_counts.columns = [
            "risk_level",
            "count",
        ]

        fig_donut = go.Figure(
            data=[
                go.Pie(
                    labels=risk_counts["risk_level"],
                    values=risk_counts["count"],
                    hole=0.62,
                    marker=dict(
                        colors=[
                            RISK_COLOR_MAP[r]
                            for r in risk_counts["risk_level"]
                        ],
                        line=dict(
                            color=COLORS["card"],
                            width=3,
                        ),
                    ),
                    textinfo="percent",
                    textfont=dict(
                        size=13,
                        color="white",
                        family="Inter",
                    ),
                )
            ]
        )

        fig_donut.update_layout(
            **PLOTLY_LAYOUT,
            height=320,
            annotations=[
                dict(
                    text=(
                        f"<b>{len(df):,}</b><br>"
                        f"<span style='font-size:11px;"
                        f"color:{COLORS['text_muted']}'>"
                        f"transactions</span>"
                    ),
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(
                        size=18,
                        color=COLORS["navy"],
                    ),
                )
            ],
        )

        st.plotly_chart(
            fig_donut,
            width="stretch",
        )

    # -----------------------------------------------------------------------
    # Transaction Value by Month
    # -----------------------------------------------------------------------

    with col_right:

        st.markdown(
            '<div class="section-title">Transaction Value by Month</div>',
            unsafe_allow_html=True,
        )

        monthly = (
            df.groupby("month")["amount"]
            .sum()
            .reset_index()
        )

        fig_line = go.Figure()

        fig_line.add_trace(
            go.Scatter(
                x=monthly["month"],
                y=monthly["amount"],
                mode="lines+markers",
                line=dict(
                    color=COLORS["accent"],
                    width=3,
                    shape="spline",
                ),
                marker=dict(
                    size=7,
                    color=COLORS["accent"],
                ),
                fill="tozeroy",
                fillcolor="rgba(44,92,224,0.08)",
            )
        )

        fig_line.update_layout(
            **PLOTLY_LAYOUT,
            height=320,
            xaxis=dict(
                title="Month",
                gridcolor=COLORS["border"],
                dtick=1,
            ),
            yaxis=dict(
                title="Total Value (₹)",
                gridcolor=COLORS["border"],
                tickformat=",.0f",
            ),
        )

        st.plotly_chart(
            fig_line,
            width="stretch",
        )

    # -----------------------------------------------------------------------
    # Rule Tests Triggered
    # -----------------------------------------------------------------------

    st.markdown(
        '<div class="section-title">Rule Tests Triggered</div>',
        unsafe_allow_html=True,
    )

    test_counts = (
        df[
            df["tests_triggered"].notna()
            & (df["tests_triggered"] != "")
        ]["tests_triggered"]
        .str.split(", ")
        .explode()
        .value_counts()
        .sort_values(ascending=True)
    )

    fig_tests = go.Figure(
        go.Bar(
            x=test_counts.values,
            y=[
                t.replace("_", " ").title()
                for t in test_counts.index
            ],
            orientation="h",
            marker=dict(
                color=COLORS["accent"],
                line=dict(width=0),
            ),
            text=test_counts.values,
            textposition="outside",
            textfont=dict(
                size=11,
                color=COLORS["text"],
            ),
        )
    )

    fig_tests.update_layout(
        **PLOTLY_LAYOUT,
        height=260,
        xaxis=dict(
            gridcolor=COLORS["border"],
            title="Transactions Flagged",
        ),
        yaxis=dict(title=""),
    )

    st.plotly_chart(
        fig_tests,
        width="stretch",
    )


# ---------------------------------------------------------------------------
# TAB 2: VENDOR RISK
# ---------------------------------------------------------------------------

with tab2:

    st.markdown(
        '<div class="section-title">Top 10 Vendors by Flagged Value</div>',
        unsafe_allow_html=True,
    )

    vendor_risk = (
        df[
            df["risk_level"].isin(["High", "Medium"])
        ]
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
            marker=dict(
                color=COLORS["navy"],
                line=dict(width=0),
            ),
            text=[
                f"₹{v / 1e6:.2f}M"
                for v in vendor_risk["amount"]
            ],
            textposition="outside",
            textfont=dict(
                size=11,
                color=COLORS["text"],
            ),
        )
    )

    fig_vendor.update_layout(
        **PLOTLY_LAYOUT,
        height=380,
        xaxis=dict(
            title="",
            tickangle=-25,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            title="Flagged Value (₹)",
            gridcolor=COLORS["border"],
            tickformat=",.0f",
        ),
    )

    st.plotly_chart(
        fig_vendor,
        width="stretch",
    )

    col_a, col_b = st.columns(2)

    # -----------------------------------------------------------------------
    # Vendor Frequency vs Amount
    # -----------------------------------------------------------------------

    with col_a:

        st.markdown(
            '<div class="section-title">Vendor Frequency vs. Amount</div>',
            unsafe_allow_html=True,
        )

        fig_scatter = px.scatter(
            df,
            x="vendor_frequency",
            y="amount",
            color="risk_level",
            color_discrete_map=RISK_COLOR_MAP,
            category_orders={
                "risk_level": RISK_ORDER
            },
            opacity=0.6,
        )

        fig_scatter.update_traces(
            marker=dict(
                size=6,
                line=dict(width=0),
            )
        )

        fig_scatter.update_layout(
            **PLOTLY_LAYOUT,
            height=340,
            xaxis=dict(
                title="Vendor Transaction Frequency",
                gridcolor=COLORS["border"],
            ),
            yaxis=dict(
                title="Amount (₹)",
                gridcolor=COLORS["border"],
            ),
        )

        st.plotly_chart(
            fig_scatter,
            width="stretch",
        )

    # -----------------------------------------------------------------------
    # Spend Share by Department
    # -----------------------------------------------------------------------

    with col_b:

        st.markdown(
            '<div class="section-title">Spend Share by Department</div>',
            unsafe_allow_html=True,
        )

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
                marker=dict(
                    color=COLORS["slate"],
                ),
            )
        )

        fig_dept.update_layout(
            **PLOTLY_LAYOUT,
            height=340,
            xaxis=dict(
                title="",
                tickangle=-20,
                tickfont=dict(size=10),
            ),
            yaxis=dict(
                title="Total Spend (₹)",
                gridcolor=COLORS["border"],
                tickformat=",.0f",
            ),
        )

        st.plotly_chart(
            fig_dept,
            width="stretch",
        )


# ---------------------------------------------------------------------------
# TAB 3: TRANSACTION DETAIL
# ---------------------------------------------------------------------------

with tab3:

    st.markdown(
        '<div class="section-title">Flagged Transactions (filtered)</div>',
        unsafe_allow_html=True,
    )

    flagged = (
        filtered[
            filtered["risk_level"].isin(["High", "Medium"])
        ]
        .sort_values(
            "risk_score",
            ascending=False,
        )
    )

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
        <span style='color:{COLORS["text_muted"]}; font-size:13px;'>
            {len(flagged):,} transactions match the current filters
        </span>
        """,
        unsafe_allow_html=True,
    )

    st.dataframe(
        flagged[display_cols]
        .style
        .format(
            {
                "amount": "₹{:,.2f}",
                "risk_score": "{:.3f}",
                "date": "{:%Y-%m-%d}",
            }
        )
        .map(
            lambda v: (
                f"color: "
                f"{RISK_COLOR_MAP.get(str(v), COLORS['text'])}; "
                f"font-weight:700;"
            ),
            subset=["risk_level"],
        ),
        width="stretch",
        height=480,
        hide_index=True,
    )
    csv_bytes = (
        flagged[display_cols]
        .to_csv(index=False)
        .encode("utf-8")
    )

    st.download_button(
        "Download filtered results (CSV)",
        data=csv_bytes,
        file_name="auditlens_flagged_transactions.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <div style='
        text-align:center;
        color:{COLORS["text_muted"]};
        font-size:11px;
        margin-top:40px;
        padding-top:16px;
        border-top:1px solid {COLORS["border"]};
    '>
        AuditLens &mdash; generated from data/dashboard_export.csv
        &middot;
        risk scoring combines rule-based audit tests and
        Isolation Forest anomaly detection
    </div>
    """,
    unsafe_allow_html=True,
)