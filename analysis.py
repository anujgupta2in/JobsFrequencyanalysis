import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(
    page_title="7 Days Jobs Analysis",
    layout="wide"
)

st.title("7 Days PMS Jobs Analysis Dashboard")

# =====================================================
# File Upload
# =====================================================

uploaded_file = st.sidebar.file_uploader(
    "Upload 7 Days Jobs Excel / CSV File",
    type=["xlsx", "xls", "csv"]
)

if uploaded_file is None:
    st.info("Please upload your consolidated Excel or CSV file.")
    st.stop()


# =====================================================
# Load Data
# =====================================================

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


# =====================================================
# Column Standardization
# =====================================================

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

df["Tags"] = df["Tags"].replace("", "Blank")
df["Job Source"] = df["Job Source"].replace("", "Blank")
df["Frequency"] = df["Frequency"].fillna("").astype(str).str.strip()

# Combined Job Code + Title filter column
df["Job"] = (
    df["Job Code"].astype(str).str.strip()
    + " - "
    + df["Title"].astype(str).str.strip()
)

# Keep 7 Days jobs only
df = df[
    df["Frequency"].str.contains("7", case=False, na=False) &
    df["Frequency"].str.contains("day", case=False, na=False)
].copy()


# =====================================================
# Sidebar Filters
# =====================================================

st.sidebar.header("Filters")

filtered_df = df.copy()

# Search box for Job Code / Title
st.sidebar.subheader("Search Job")

search_job = st.sidebar.text_input(
    "Search by Job Code or Title"
)

if search_job:
    filtered_df = filtered_df[
        filtered_df["Job"].str.contains(search_job, case=False, na=False)
    ]

filter_cols = [
    "Vessel",
    "Function",
    "Machinery Location",
    "Sub Component Location",
    "Job",
    "Job Code",
    "Title",
    "Critical",
    "Tags",
    "Job Source",
    "Frequency"
]

for col in filter_cols:
    options = sorted(filtered_df[col].dropna().unique())

    selected = st.sidebar.multiselect(
        f"Filter by {col}",
        options
    )

    if selected:
        filtered_df = filtered_df[filtered_df[col].isin(selected)]


# =====================================================
# KPI Section
# =====================================================

st.subheader("Fleet Summary")

total_jobs = len(filtered_df)
total_vessels = filtered_df["Vessel"].nunique()
critical_jobs = (filtered_df["Critical"] == "Critical").sum()
non_critical_jobs = total_jobs - critical_jobs
critical_pct = round((critical_jobs / total_jobs * 100), 2) if total_jobs else 0

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Jobs", total_jobs)
col2.metric("Total Vessels", total_vessels)
col3.metric("Critical Jobs", critical_jobs)
col4.metric("Non-Critical Jobs", non_critical_jobs)
col5.metric("Critical %", f"{critical_pct}%")


# =====================================================
# Tabs
# =====================================================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Vessel Summary",
    "Tags Analysis",
    "Job Source",
    "Function / Machinery",
    "Pivot Table",
    "Raw Data"
])


# =====================================================
# Vessel Summary
# =====================================================

with tab1:
    st.subheader("Vessel-wise Summary")

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

    vessel_summary = vessel_summary.sort_values("Total_Jobs", ascending=False)

    st.dataframe(vessel_summary, use_container_width=True)

    st.subheader("Top Vessels by Total Jobs")

    top_n = st.slider("Number of vessels to show", 5, 100, 30)

    top_vessels = vessel_summary.head(top_n).set_index("Vessel")[
        ["Total_Jobs", "Critical_Jobs", "Non_Critical_Jobs"]
    ]

    st.bar_chart(top_vessels)


# =====================================================
# Tags Analysis
# =====================================================

with tab2:
    st.subheader("Tag Summary")

    tag_summary = (
        filtered_df.groupby("Tags")
        .size()
        .reset_index(name="Job Count")
        .sort_values("Job Count", ascending=False)
    )

    st.dataframe(tag_summary, use_container_width=True)

    st.bar_chart(tag_summary.set_index("Tags"))

    st.subheader("Vessel vs Tags")

    vessel_tag = (
        filtered_df.groupby(["Vessel", "Tags"])
        .size()
        .reset_index(name="Job Count")
        .sort_values("Job Count", ascending=False)
    )

    st.dataframe(vessel_tag, use_container_width=True)


# =====================================================
# Job Source
# =====================================================

with tab3:
    st.subheader("Job Source Summary")

    source_summary = (
        filtered_df.groupby("Job Source")
        .size()
        .reset_index(name="Job Count")
        .sort_values("Job Count", ascending=False)
    )

    st.dataframe(source_summary, use_container_width=True)

    st.bar_chart(source_summary.set_index("Job Source"))

    st.subheader("Job Source vs Criticality")

    source_critical = (
        filtered_df.groupby(["Job Source", "Critical"])
        .size()
        .reset_index(name="Job Count")
    )

    st.dataframe(source_critical, use_container_width=True)


# =====================================================
# Function / Machinery
# =====================================================

with tab4:
    st.subheader("Function Summary")

    function_summary = (
        filtered_df.groupby("Function")
        .size()
        .reset_index(name="Job Count")
        .sort_values("Job Count", ascending=False)
    )

    st.dataframe(function_summary, use_container_width=True)

    st.bar_chart(function_summary.head(30).set_index("Function"))

    st.subheader("Machinery Location Summary")

    machinery_summary = (
        filtered_df.groupby("Machinery Location")
        .size()
        .reset_index(name="Job Count")
        .sort_values("Job Count", ascending=False)
    )

    st.dataframe(machinery_summary, use_container_width=True)

    st.bar_chart(machinery_summary.head(30).set_index("Machinery Location"))


# =====================================================
# Dynamic Pivot Table
# =====================================================

with tab5:
    st.subheader("Dynamic Pivot Table")

    pivot_cols = list(filtered_df.columns)

    row_fields = st.multiselect(
        "Select Row Field(s)",
        pivot_cols,
        default=["Vessel"]
    )

    column_field = st.selectbox(
        "Select Column Field",
        ["None"] + pivot_cols,
        index=0
    )

    value_field = st.selectbox(
        "Select Value Field",
        pivot_cols,
        index=pivot_cols.index("Job Code") if "Job Code" in pivot_cols else 0
    )

    agg_option = st.selectbox(
        "Aggregation",
        ["Count", "Nunique"]
    )

    aggfunc = "count" if agg_option == "Count" else pd.Series.nunique

    if not row_fields:
        st.warning("Please select at least one Row Field.")
    else:
        try:
            if column_field == "None":
                pivot_table = (
                    filtered_df.groupby(row_fields)[value_field]
                    .agg(aggfunc)
                    .reset_index(name="Value")
                    .sort_values("Value", ascending=False)
                )
            else:
                pivot_table = pd.pivot_table(
                    filtered_df,
                    index=row_fields,
                    columns=column_field,
                    values=value_field,
                    aggfunc=aggfunc,
                    fill_value=0
                ).reset_index()

            st.dataframe(pivot_table, use_container_width=True)

            st.subheader("Pivot Chart")

            chart_df = pivot_table.copy()

            if column_field == "None":
                if len(row_fields) == 1:
                    chart_df = chart_df.head(50).set_index(row_fields[0])
                    st.bar_chart(chart_df["Value"])
                else:
                    chart_df["Combined"] = chart_df[row_fields].astype(str).agg(" | ".join, axis=1)
                    chart_df = chart_df.head(50).set_index("Combined")
                    st.bar_chart(chart_df["Value"])
            else:
                if len(row_fields) == 1:
                    chart_df = chart_df.set_index(row_fields[0])
                    numeric_cols = chart_df.select_dtypes(include="number").columns
                    st.bar_chart(chart_df[numeric_cols].head(50))

        except Exception as e:
            st.error(f"Pivot error: {e}")


# =====================================================
# Raw Data
# =====================================================

with tab6:
    st.subheader("Filtered Raw Data")
    st.dataframe(filtered_df, use_container_width=True)


# =====================================================
# Download Excel
# =====================================================

def create_excel_download():
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        filtered_df.to_excel(writer, index=False, sheet_name="Filtered Data")
        vessel_summary.to_excel(writer, index=False, sheet_name="Vessel Summary")
        tag_summary.to_excel(writer, index=False, sheet_name="Tag Summary")
        source_summary.to_excel(writer, index=False, sheet_name="Job Source Summary")
        function_summary.to_excel(writer, index=False, sheet_name="Function Summary")

    return output.getvalue()


st.sidebar.download_button(
    label="Download Analysis Excel",
    data=create_excel_download(),
    file_name="7_Days_Jobs_Analysis_Output.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
