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
st.title("🏗️ Kerem's Primavera P6 Viewer & Gantt Chart")

uploaded_file = st.file_uploader("Upload .xer file", type=['xer'])

if uploaded_file:
    df = parse_xer_table(uploaded_file, "TASK")

    if df is not None:
                # --- IMPROVED DATE HANDLING ---
        date_cols = ['early_start_date', 'early_end_date', 'act_start_date', 'act_end_date']
        for col in date_cols:
            if col in df.columns:
                # Convert to datetime, turn errors into 'NaT' (Not a Time)
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Create Start/Finish columns using Actuals first, then Early dates
        df['Start'] = df['act_start_date'].fillna(df['early_start_date'])
        df['Finish'] = df['act_end_date'].fillna(df['early_end_date'])

        # CRITICAL FIX: Ensure dates are not null and Finish is AFTER Start
        df_plot = df.dropna(subset=['Start', 'Finish']).copy()
        df_plot = df_plot[df_plot['Finish'] > df_plot['Start']]

    # --- FIXED GANTT CHART SECTION ---
        st.subheader("Interactive Gantt Chart")
        if not df_plot.empty:
            try:
                # Limit to first 200 tasks for performance
                if len(df_plot) > 200:
                    st.warning("Showing first 200 activities. Use the sidebar to search for specific tasks.")
                    df_plot = df_plot.head(200)

                # Fix: Use x_start and x_end instead of start and finish
                fig = px.timeline(
                    df_plot, 
                    x_start="Start", 
                    x_end="Finish", 
                    y="task_name", 
                    color="status_code",
                    hover_data=['task_code'],
                    labels={"status_code": "Status", "task_name": "Activity"}
                )
                
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"Gantt Error: {e}")
        else:
            st.warning("No valid activities with both a Start and Finish date were found.")




        # --- Data Table ---
        st.subheader("Activity Details")
        st.dataframe(df, use_container_width=True)

    else:
        st.error("No TASK table found in file.")



