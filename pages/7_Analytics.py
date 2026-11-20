"""
Analytics & Trends Page.
Visualizes academic metrics, subject-wise attendance rankings,
and defaulter reports mirroring the PL/SQL cursor logic.
"""

import streamlit as st
import pandas as pd
import db
import queries

st.set_page_config(page_title="Academic Analytics", page_icon="📊", layout="wide")
db.render_sidebar()

st.title("📊 Academic Analytics & Insights")
st.markdown("Visual attendance distribution, subject performance benchmarks, and defaulter tracking.")

tab_trend, tab_cursor, tab_dept = st.tabs([
    "📈 Subject Attendance Ranking",
    "⚠️ Defaulters List (Cursor Equivalent)",
    "🏫 Department & Semester Overview"
])

# -----------------------------------------------------------------------------
# TAB 1: SUBJECT ATTENDANCE RANKING
# -----------------------------------------------------------------------------
with tab_trend:
    st.subheader("Subject-Wise Attendance Trend")
    st.caption("Runs: `SELECT subid, ... ORDER BY attendance_percentage DESC`")

    trend_df = db.run_query(queries.GET_SUBJECT_WISE_ATTENDANCE_TREND)

    if trend_df.empty:
        st.warning("No attendance data available to generate trends.")
    else:
        col_c, col_t = st.columns([3, 2])

        with col_c:
            st.markdown("##### Average Attendance (%) by Subject")
            chart_data = trend_df.copy()
            # Set index for clean bar chart
            chart_data["label"] = chart_data["subid"] + " (" + chart_data["subject_name"].fillna("") + ")"
            chart_data = chart_data.set_index("label")
            st.bar_chart(chart_data["attendance_percentage"], color="#1E88E5")

        with col_t:
            st.markdown("##### Subject Metrics")
            st.dataframe(
                trend_df.rename(columns={
                    "subid": "Subject Code",
                    "subject_name": "Subject Title",
                    "attendance_percentage": "Avg Attendance (%)",
                    "total_records": "Total Entries"
                }),
                use_container_width=True,
                hide_index=True
            )

# -----------------------------------------------------------------------------
# TAB 2: DEFAULTERS LIST (CURSOR EQUIVALENT)
# -----------------------------------------------------------------------------
with tab_cursor:
    st.subheader("⚠️ Low Attendance Defaulter List (< 75%)")
    st.caption("Implements the logic of the PL/SQL cursor: identifies students with overall attendance < 75%.")

    defaulters_df = db.run_query(queries.GET_CURSOR_LOW_ATTENDANCE)

    if defaulters_df.empty:
        st.success("🎉 No students have overall attendance below 75%!")
    else:
        st.error(f"⚠️ **{len(defaulters_df)}** student(s) identified with attendance under the 75% academic threshold.")

        # Metric cards for defaulters
        for idx, row in defaulters_df.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 2, 2, 2])
                c1.markdown(f"**ID**: `{row['sid']}`")
                c2.markdown(f"**Name**: {row['student_name']}")
                c3.markdown(f"**Attended**: {int(row['attended_classes'])} / {int(row['total_classes'])} classes")
                c4.metric("Attendance", f"{row['att_per']}%", delta=f"{row['att_per'] - 75:.1f}%", delta_color="inverse")

        st.markdown("---")
        st.dataframe(
            defaulters_df.rename(columns={
                "sid": "Student ID",
                "student_name": "Student Name",
                "att_per": "Overall Attendance (%)",
                "attended_classes": "Present Classes",
                "total_classes": "Total Classes"
            }),
            use_container_width=True,
            hide_index=True
        )

# -----------------------------------------------------------------------------
# TAB 3: DEPARTMENT & SEMESTER OVERVIEW
# -----------------------------------------------------------------------------
with tab_dept:
    st.subheader("Department & Semester Demographics")

    stu_all = db.run_query(queries.GET_ALL_STUDENTS)

    if stu_all.empty:
        st.info("No student data available.")
    else:
        c_d1, c_d2 = st.columns(2)

        with c_d1:
            st.markdown("##### Students per Department")
            dept_counts = stu_all["dept"].value_counts().reset_index()
            dept_counts.columns = ["Department", "Student Count"]
            st.dataframe(dept_counts, use_container_width=True, hide_index=True)

        with c_d2:
            st.markdown("##### Students per Semester")
            stu_all["semester_number"] = stu_all["sem"].map(db.parse_student_semester)
            sem_counts = (
                stu_all.dropna(subset=["semester_number"])["semester_number"]
                .value_counts()
                .sort_index()
                .reset_index()
            )
            sem_counts.columns = ["Semester", "Student Count"]
            sem_counts["Semester"] = "Sem " + sem_counts["Semester"].astype(str)
            st.bar_chart(sem_counts.set_index("Semester"))
