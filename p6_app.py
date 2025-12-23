import streamlit as st
import pandas as pd
import plotly.express as px
import io

def parse_xer_table(file_buffer, table_name="TASK"):
    content = file_buffer.getvalue().decode('latin1', errors='ignore')
    lines = content.splitlines()
    headers = []
    rows = []
    reading_target_table = False
    
    for line in lines:
        parts = line.split('\t')
        row_type = parts[0]
        if row_type == '%T':
            reading_target_table = (parts[1].strip() == table_name)
            continue
        if reading_target_table and row_type == '%F':
            headers = parts[1:]
            continue
        if reading_target_table and row_type == '%R':
            values = parts[1:]
            if len(values) < len(headers):
                values += [''] * (len(headers) - len(values))
            rows.append(values)

    return pd.DataFrame(rows, columns=headers) if headers else None

# --- UI Setup ---
st.set_page_config(layout="wide", page_title="P6 Viewer + Gantt")
st.title("🏗️ Primavera P6 Viewer & Gantt Chart")

uploaded_file = st.file_uploader("Upload .xer file", type=['xer'])

if uploaded_file:
    df = parse_xer_table(uploaded_file, "TASK")

    if df is not None:
        # 1. Date Pre-processing (P6 dates are often YYYY-MM-DD HH:MM)
        # We use early_start_date and early_end_date as defaults
        date_cols = ['early_start_date', 'early_end_date', 'act_start_date', 'act_end_date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Create a display column for Start/End to use in the Gantt
        df['Start'] = df['act_start_date'].fillna(df['early_start_date'])
        df['Finish'] = df['act_end_date'].fillna(df['early_end_date'])

        # Filter out rows without dates (milestones with only one date or empty rows)
        df_plot = df.dropna(subset=['Start', 'Finish'])

        # --- Sidebar Filters ---
        st.sidebar.header("Filters")
        search = st.sidebar.text_input("Search Activity Name", "")
        if search:
            df_plot = df_plot[df_plot['task_name'].str.contains(search, case=False)]

        # --- Metrics ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Activities", len(df))
        col2.metric("Plotted on Gantt", len(df_plot))
        
        # --- Gantt Chart ---
        st.subheader("Interactive Gantt Chart")
        if not df_plot.empty:
            fig = px.timeline(
                df_plot, 
                start="Start", 
                finish="Finish", 
                x_start="Start", 
                x_end="Finish", 
                y="task_name", 
                color="status_code",
                hover_data=['task_code', 'total_float'],
                title="Project Schedule",
                labels={"status_code": "Status", "task_name": "Activity"}
            )
            fig.update_yaxes(autorange="reversed") # Highest activity at the top
            fig.update_layout(height=600, margin=dict(t=30, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No valid start/end dates found to plot the Gantt chart.")

        # --- Data Table ---
        st.subheader("Activity Details")
        st.dataframe(df, use_container_width=True)

    else:
        st.error("No TASK table found in file.")
