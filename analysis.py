import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from io import BytesIO

st.set_page_config(
    page_title="7 Days Jobs Analysis",
    layout="wide"
)

st.title("7 Days PMS Jobs Analysis Dashboard")

# =========================
# File Upload / Default Path
# =========================

default_file = Path(r"C:\Users\guptaanu\Downloads\7_Days_Jobs_Consolidated_With_Analysis.xlsx")

uploaded_file = st.sidebar.file_uploader(
    "Upload Consolidated Excel File",
    type=["xlsx", "xls", "csv"]
)

@st.cache_data
def load_data(file):
    if file is not None:
        if file.name.endswith(".csv"):
            return pd.read_csv(file, dtype=str)
        else:
            return pd.read_excel(file, sheet_name="7 Days Jobs", dtype=str)
    else:
        return pd.read_excel(default_file, sheet_name="7 Days Jobs", dtype=str)

try:
    df = load_data(uploaded_file)
except Exception as e:
    st.error(f"Error loading file: {e}")
    st.stop()

# =========================
# Data Cleaning
# =========================

df.columns = df.columns.str.strip()

for col in df.columns:
    df[col] = df[col].fillna("").astype(str).str.strip()

if "Tags" in df.columns:
    df["Tags"] = df["Tags"].replace("", "Blank")

if "Critical" in df.columns:
    df["Critical"] = df["Critical"].replace({
        "C": "Critical",
        "": "Non-Critical"
    })

required_cols = [
    "Vessel",
    "Function",
    "Machinery Location",
    "Sub Component Location",
    "Job Code",
    "Title",
    "Critical",
    "Frequency",
    "Tags",
    "Job Source"
]

missing_cols = [col for col in required_cols if col not in df.columns]

if missing_cols:
    st.warning(f"Missing columns in file: {missing_cols}")

# =========================
# Sidebar Filters
# =========================

st.sidebar.header("Filters")

filter_cols = [
    col for col in [
        "Vessel",
        "Function",
        "Machinery Location",
        "Sub Component Location",
        "Critical",
        "Tags",
        "Job Source",
        "Frequency"
    ]
    if col in df.columns
]

filtered_df = df.copy()

for col in filter_cols:
    values = sorted(filtered_df[col].dropna().unique())
    selected = st.sidebar.multiselect(
        f"Filter by {col}",
        values,
        default=[]
    )

    if selected:
        filtered_df = filtered_df[filtered_df[col].isin(selected)]

# =========================
# KPI Section
# =========================

st.subheader("Fleet Summary")

total_jobs = len(filtered_df)
total_vessels = filtered_df["Vessel"].nunique() if "Vessel" in filtered_df.columns else 0
critical_jobs = len(filtered_df[filtered_df["Critical"] == "Critical"]) if "Critical" in filtered_df.columns else 0
non_critical_jobs = total_jobs - critical_jobs

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Jobs", total_jobs)
col2.metric("Total Vessels", total_vessels)
col3.metric("Critical Jobs", critical_jobs)
col4.metric("Non-Critical Jobs", non_critical_jobs)

# =========================
# Tabs
# =========================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Vessel Analysis",
    "Critical Analysis",
    "Tags Analysis",
    "Combination Analysis",
    "Pivot Table",
    "Raw Data"
])

# =========================
# Vessel Analysis
# =========================

with tab1:
    st.subheader("Vessel-wise Job Count")

    if "Vessel" in filtered_df.columns:
        vessel_summary = (
            filtered_df.groupby("Vessel")
            .size()
            .reset_index(name="Total Jobs")
            .sort_values("Total Jobs", ascending=False)
        )

        st.dataframe(vessel_summary, use_container_width=True)

        fig = px.bar(
            vessel_summary.head(30),
            x="Vessel",
            y="Total Jobs",
            title="Top 30 Vessels by 7-Day Jobs",
            text="Total Jobs"
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

# =========================
# Critical Analysis
# =========================

with tab2:
    st.subheader("Critical vs Non-Critical Analysis")

    if all(col in filtered_df.columns for col in ["Vessel", "Critical"]):
        critical_summary = (
            filtered_df.groupby(["Vessel", "Critical"])
            .size()
            .reset_index(name="Job Count")
        )

        pivot_critical = critical_summary.pivot_table(
            index="Vessel",
            columns="Critical",
            values="Job Count",
            fill_value=0
        ).reset_index()

        pivot_critical["Total Jobs"] = pivot_critical.drop(columns=["Vessel"]).sum(axis=1)

        if "Critical" in pivot_critical.columns:
            pivot_critical["Critical %"] = (
                pivot_critical["Critical"] / pivot_critical["Total Jobs"] * 100
            ).round(2)

        pivot_critical = pivot_critical.sort_values("Total Jobs", ascending=False)

        st.dataframe(pivot_critical, use_container_width=True)

        fig = px.bar(
            critical_summary,
            x="Vessel",
            y="Job Count",
            color="Critical",
            title="Critical / Non-Critical Jobs by Vessel"
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

# =========================
# Tags Analysis
# =========================

with tab3:
    st.subheader("Tags Analysis")

    if "Tags" in filtered_df.columns:
        tag_summary = (
            filtered_df.groupby("Tags")
            .size()
            .reset_index(name="Job Count")
            .sort_values("Job Count", ascending=False)
        )

        st.dataframe(tag_summary, use_container_width=True)

        fig = px.bar(
            tag_summary,
            x="Tags",
            y="Job Count",
            title="Jobs by Tags",
            text="Job Count"
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Vessel-wise Tag Distribution")

    if all(col in filtered_df.columns for col in ["Vessel", "Tags"]):
        vessel_tag = (
            filtered_df.groupby(["Vessel", "Tags"])
            .size()
            .reset_index(name="Job Count")
        )

        st.dataframe(vessel_tag, use_container_width=True)

        fig = px.bar(
            vessel_tag,
            x="Vessel",
            y="Job Count",
            color="Tags",
            title="Tag Distribution by Vessel"
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

# =========================
# Combination Analysis
# =========================

with tab4:
    st.subheader("Combination Analysis")

    available_cols = [col for col in filtered_df.columns if col not in ["Title"]]

    group_cols = st.multiselect(
        "Select columns for combination analysis",
        available_cols,
        default=["Vessel", "Critical"] if "Vessel" in available_cols and "Critical" in available_cols else []
    )

    if group_cols:
        combo_summary = (
            filtered_df.groupby(group_cols)
            .size()
            .reset_index(name="Job Count")
            .sort_values("Job Count", ascending=False)
        )

        st.dataframe(combo_summary, use_container_width=True)

        if len(group_cols) == 1:
            fig = px.bar(
                combo_summary.head(50),
                x=group_cols[0],
                y="Job Count",
                title=f"Jobs by {group_cols[0]}",
                text="Job Count"
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        elif len(group_cols) >= 2:
            fig = px.bar(
                combo_summary.head(100),
                x=group_cols[0],
                y="Job Count",
                color=group_cols[1],
                title=f"Jobs by {group_cols[0]} and {group_cols[1]}"
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

# =========================
# Pivot Table
# =========================

with tab5:
    st.subheader("Custom Pivot Table")

    available_cols = list(filtered_df.columns)

    row_col = st.selectbox("Select Row Column", available_cols, index=0)
    col_col = st.selectbox(
        "Select Column Field",
        ["None"] + available_cols,
        index=0
    )

    value_col = st.selectbox(
        "Select Value Column",
        available_cols,
        index=available_cols.index("Job Code") if "Job Code" in available_cols else 0
    )

    if col_col == "None":
        pivot = (
            filtered_df.groupby(row_col)[value_col]
            .count()
            .reset_index(name="Count")
            .sort_values("Count", ascending=False)
        )
    else:
        pivot = pd.pivot_table(
            filtered_df,
            index=row_col,
            columns=col_col,
            values=value_col,
            aggfunc="count",
            fill_value=0
        ).reset_index()

    st.dataframe(pivot, use_container_width=True)

# =========================
# Raw Data
# =========================

with tab6:
    st.subheader("Filtered Raw Data")
    st.dataframe(filtered_df, use_container_width=True)

# =========================
# Download Filtered Data
# =========================

def convert_to_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Filtered Data")
    return output.getvalue()

excel_data = convert_to_excel(filtered_df)

st.sidebar.download_button(
    label="Download Filtered Excel",
    data=excel_data,
    file_name="Filtered_7_Days_Jobs_Analysis.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)