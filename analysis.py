import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

st.set_page_config(
    page_title="7 Days Jobs Analysis",
    layout="wide"
)

st.title("7 Days PMS Jobs Analysis Dashboard")

# =========================
# Upload File
# =========================

uploaded_file = st.sidebar.file_uploader(
    "Upload Consolidated Excel / CSV File",
    type=["xlsx", "xls", "csv"]
)

if uploaded_file is None:
    st.info("Please upload the consolidated 7 Days Jobs Excel or CSV file.")
    st.stop()


# =========================
# Load Data
# =========================

@st.cache_data
def load_data(file):
    if file.name.lower().endswith(".csv"):
        return pd.read_csv(file, dtype=str)

    try:
        return pd.read_excel(file, sheet_name="7 Days Jobs", dtype=str)
    except Exception:
        return pd.read_excel(file, dtype=str)


df = load_data(uploaded_file)

df.columns = df.columns.str.strip()

for col in df.columns:
    df[col] = df[col].fillna("").astype(str).str.strip()

# =========================
# Column Cleaning
# =========================

if "Unnamed: 1" in df.columns and "Critical" not in df.columns:
    df = df.rename(columns={"Unnamed: 1": "Critical"})

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

for col in required_cols:
    if col not in df.columns:
        df[col] = ""

df["Critical"] = (
    df["Critical"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.upper()
)

df["Critical"] = df["Critical"].replace({
    "C": "Critical",
    "CRITICAL": "Critical",
    "": "Non-Critical",
    "NAN": "Non-Critical",
    "NONE": "Non-Critical"
})

df.loc[~df["Critical"].isin(["Critical"]), "Critical"] = "Non-Critical"

df["Tags"] = df["Tags"].fillna("").astype(str).str.strip()
df.loc[df["Tags"] == "", "Tags"] = "Blank"

df["Job Source"] = df["Job Source"].fillna("").astype(str).str.strip()
df.loc[df["Job Source"] == "", "Job Source"] = "Blank"

df["Frequency"] = df["Frequency"].fillna("").astype(str).str.strip()

# Keep only 7 Days if Frequency column exists
df = df[
    df["Frequency"].str.contains("7", case=False, na=False) &
    df["Frequency"].str.contains("day", case=False, na=False)
].copy()

# =========================
# Sidebar Filters
# =========================

st.sidebar.header("Filters")

filtered_df = df.copy()

filter_columns = [
    "Vessel",
    "Function",
    "Machinery Location",
    "Sub Component Location",
    "Critical",
    "Tags",
    "Job Source",
    "Frequency"
]

for col in filter_columns:
    if col in filtered_df.columns:
        options = sorted(filtered_df[col].dropna().unique())
        selected = st.sidebar.multiselect(
            f"{col}",
            options
        )

        if selected:
            filtered_df = filtered_df[filtered_df[col].isin(selected)]

# =========================
# KPIs
# =========================

st.subheader("Fleet Summary")

total_jobs = len(filtered_df)
total_vessels = filtered_df["Vessel"].nunique()
critical_jobs = len(filtered_df[filtered_df["Critical"] == "Critical"])
non_critical_jobs = total_jobs - critical_jobs
critical_percent = round((critical_jobs / total_jobs * 100), 2) if total_jobs else 0

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Jobs", total_jobs)
col2.metric("Total Vessels", total_vessels)
col3.metric("Critical Jobs", critical_jobs)
col4.metric("Non-Critical Jobs", non_critical_jobs)
col5.metric("Critical %", f"{critical_percent}%")

# =========================
# Tabs
# =========================

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Vessel Summary",
    "Critical Analysis",
    "Tags Analysis",
    "Job Source",
    "Function / Machinery",
    "Custom Combination",
    "Raw Data"
])

# =========================
# Tab 1 Vessel Summary
# =========================

with tab1:
    st.subheader("Vessel-wise Job Summary")

    vessel_summary = (
        filtered_df.groupby("Vessel")
        .agg(
            Total_Jobs=("Job Code", "count"),
            Critical_Jobs=("Critical", lambda x: (x == "Critical").sum()),
            Non_Critical_Jobs=("Critical", lambda x: (x != "Critical").sum()),
            Unique_Functions=("Function", "nunique"),
            Unique_Machinery=("Machinery Location", "nunique")
        )
        .reset_index()
    )

    vessel_summary["Critical %"] = (
        vessel_summary["Critical_Jobs"] /
        vessel_summary["Total_Jobs"] * 100
    ).round(2)

    vessel_summary = vessel_summary.sort_values(
        "Total_Jobs",
        ascending=False
    )

    st.dataframe(vessel_summary, use_container_width=True)

    top_n = st.slider("Select Top N Vessels", 5, 100, 30)

    fig = px.bar(
        vessel_summary.head(top_n),
        x="Vessel",
        y="Total_Jobs",
        text="Total_Jobs",
        title=f"Top {top_n} Vessels by 7-Day Jobs"
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(
        vessel_summary.head(top_n),
        x="Vessel",
        y=["Critical_Jobs", "Non_Critical_Jobs"],
        title=f"Critical vs Non-Critical Jobs - Top {top_n} Vessels"
    )
    fig2.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig2, use_container_width=True)

# =========================
# Tab 2 Critical Analysis
# =========================

with tab2:
    st.subheader("Critical vs Non-Critical Analysis")

    critical_summary = (
        filtered_df.groupby("Critical")
        .size()
        .reset_index(name="Job Count")
    )

    st.dataframe(critical_summary, use_container_width=True)

    fig = px.pie(
        critical_summary,
        names="Critical",
        values="Job Count",
        title="Critical vs Non-Critical Distribution"
    )
    st.plotly_chart(fig, use_container_width=True)

    vessel_critical = (
        filtered_df.groupby(["Vessel", "Critical"])
        .size()
        .reset_index(name="Job Count")
    )

    fig2 = px.bar(
        vessel_critical,
        x="Vessel",
        y="Job Count",
        color="Critical",
        title="Critical / Non-Critical by Vessel"
    )
    fig2.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig2, use_container_width=True)

# =========================
# Tab 3 Tags Analysis
# =========================

with tab3:
    st.subheader("Tags Analysis")

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
        text="Job Count",
        title="Jobs by Tags"
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    vessel_tag = (
        filtered_df.groupby(["Vessel", "Tags"])
        .size()
        .reset_index(name="Job Count")
    )

    fig2 = px.bar(
        vessel_tag,
        x="Vessel",
        y="Job Count",
        color="Tags",
        title="Tag Distribution by Vessel"
    )
    fig2.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig2, use_container_width=True)

# =========================
# Tab 4 Job Source
# =========================

with tab4:
    st.subheader("Job Source Analysis")

    source_summary = (
        filtered_df.groupby("Job Source")
        .size()
        .reset_index(name="Job Count")
        .sort_values("Job Count", ascending=False)
    )

    st.dataframe(source_summary, use_container_width=True)

    fig = px.bar(
        source_summary,
        x="Job Source",
        y="Job Count",
        text="Job Count",
        title="Jobs by Job Source"
    )
    st.plotly_chart(fig, use_container_width=True)

    source_critical = (
        filtered_df.groupby(["Job Source", "Critical"])
        .size()
        .reset_index(name="Job Count")
    )

    fig2 = px.bar(
        source_critical,
        x="Job Source",
        y="Job Count",
        color="Critical",
        title="Job Source vs Criticality"
    )
    st.plotly_chart(fig2, use_container_width=True)

# =========================
# Tab 5 Function / Machinery
# =========================

with tab5:
    st.subheader("Function and Machinery Analysis")

    function_summary = (
        filtered_df.groupby("Function")
        .size()
        .reset_index(name="Job Count")
        .sort_values("Job Count", ascending=False)
    )

    st.dataframe(function_summary, use_container_width=True)

    fig = px.bar(
        function_summary.head(30),
        x="Function",
        y="Job Count",
        text="Job Count",
        title="Top 30 Functions by Job Count"
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    machinery_summary = (
        filtered_df.groupby("Machinery Location")
        .size()
        .reset_index(name="Job Count")
        .sort_values("Job Count", ascending=False)
    )

    st.subheader("Top Machinery Locations")

    st.dataframe(machinery_summary, use_container_width=True)

    fig2 = px.bar(
        machinery_summary.head(30),
        x="Machinery Location",
        y="Job Count",
        text="Job Count",
        title="Top 30 Machinery Locations by Job Count"
    )
    fig2.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig2, use_container_width=True)

# =========================
# Tab 6 Custom Combination
# =========================

with tab6:
    st.subheader("Custom Combination Analysis")

    available_cols = [
        "Vessel",
        "Function",
        "Machinery Location",
        "Sub Component Location",
        "Critical",
        "Frequency",
        "Tags",
        "Job Source",
        "Job Code",
        "Title"
    ]

    available_cols = [col for col in available_cols if col in filtered_df.columns]

    group_cols = st.multiselect(
        "Select columns to group by",
        available_cols,
        default=["Vessel", "Critical"] if "Vessel" in available_cols and "Critical" in available_cols else []
    )

    if group_cols:
        combo = (
            filtered_df.groupby(group_cols)
            .size()
            .reset_index(name="Job Count")
            .sort_values("Job Count", ascending=False)
        )

        st.dataframe(combo, use_container_width=True)

        if len(group_cols) == 1:
            fig = px.bar(
                combo.head(50),
                x=group_cols[0],
                y="Job Count",
                text="Job Count",
                title=f"Jobs by {group_cols[0]}"
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        else:
            fig = px.bar(
                combo.head(100),
                x=group_cols[0],
                y="Job Count",
                color=group_cols[1],
                title=f"Jobs by {group_cols[0]} and {group_cols[1]}"
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

# =========================
# Tab 7 Raw Data
# =========================

with tab7:
    st.subheader("Filtered Raw Data")
    st.dataframe(filtered_df, use_container_width=True)

# =========================
# Download Section
# =========================

def to_excel(dataframes):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframes["Filtered Data"].to_excel(writer, index=False, sheet_name="Filtered Data")

        vessel_summary.to_excel(writer, index=False, sheet_name="Vessel Summary")
        tag_summary.to_excel(writer, index=False, sheet_name="Tag Summary")
        source_summary.to_excel(writer, index=False, sheet_name="Job Source Summary")
        function_summary.to_excel(writer, index=False, sheet_name="Function Summary")

    return output.getvalue()


download_data = to_excel({
    "Filtered Data": filtered_df
})

st.sidebar.download_button(
    label="Download Analysis Excel",
    data=download_data,
    file_name="7_Days_Jobs_Streamlit_Analysis.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
