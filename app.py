"""
Student Attendance & Leave Management System - Main Application Entry Point.
"""

import streamlit as st
import pandas as pd
import db
import queries

# 1. Page Configuration
st.set_page_config(
    page_title="Attendance & Leave System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Render Sidebar
db.render_sidebar()

# 3. Main Dashboard Layout
st.title("🎓 Student Attendance & Leave Management System")
st.markdown(
    "Welcome to the **Oracle-backed Academic Portal**. Use the sidebar to navigate through "
    "different modules or review the quick statistics and actions below."
)

st.markdown("---")

# 4. Check Connection & Display System KPI Metrics
is_conn, status_or_msg = db.test_connection()

if is_conn:
    # Fetch Counts for Metrics
    with st.spinner("Loading portal summary..."):
        stu_df = db.run_query(queries.GET_DASHBOARD_METRICS["total_students"])
        fac_df = db.run_query(queries.GET_DASHBOARD_METRICS["total_faculty"])
        sub_df = db.run_query(queries.GET_DASHBOARD_METRICS["total_subjects"])
        att_df = db.run_query(queries.GET_DASHBOARD_METRICS["total_attendance"])
        leave_df = db.run_query(queries.GET_DASHBOARD_METRICS["pending_leaves"])
        low_att_df = db.run_query(queries.GET_DASHBOARD_METRICS["low_attendance_students"])

        total_students = stu_df.iloc[0]["cnt"] if not stu_df.empty else 0
        total_faculty = fac_df.iloc[0]["cnt"] if not fac_df.empty else 0
        total_subjects = sub_df.iloc[0]["cnt"] if not sub_df.empty else 0
        total_attendance = att_df.iloc[0]["cnt"] if not att_df.empty else 0
        pending_leaves = leave_df.iloc[0]["cnt"] if not leave_df.empty else 0
        low_att_students = low_att_df.iloc[0]["cnt"] if not low_att_df.empty else 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("👩‍🎓 Students", total_students)
    col2.metric("👨‍🏫 Faculty", total_faculty)
    col3.metric("📚 Subjects", total_subjects)
    col4.metric("📝 Attendance Logs", total_attendance)
    col5.metric("⏳ Pending Leaves", pending_leaves, delta=f"{pending_leaves} action needed" if pending_leaves > 0 else None, delta_color="inverse")
    col6.metric("⚠️ Low Att. (<75%)", low_att_students, delta=f"{low_att_students} alerts" if low_att_students > 0 else None, delta_color="inverse")

    st.markdown("---")

    # Module Cards Grid
    st.subheader("📌 System Modules")
    m_col1, m_col2 = st.columns(2)

    with m_col1:
        with st.container(border=True):
            st.markdown("### 👩‍🏫 Faculty Directory (`1_Faculty`)")
            st.write("Manage professors and instructors, departments, contact emails, and course assignments.")
            st.markdown("- Full CRUD (Add, View, Update, Remove)\n- Sort by name and filter by ID")

        with st.container(border=True):
            st.markdown("### 📚 Subjects & Curriculum (`3_Subject`)")
            st.write("Manage courses, credit allocations, semester mappings, and assigned faculty leads.")
            st.markdown("- Linked directly to Faculty Foreign Keys\n- Enforces credits and semester bounds (1-8)")

        with m_col1:
            with st.container(border=True):
                st.markdown("### 📝 Attendance Portal (`5_Attendance`)")
                st.write("Daily session attendance recording, batch marking, history lookups, and per-student percentage calculation.")
                st.markdown("- Single & bulk daily marking\n- Calls PL/SQL `attfunction(sid, subid)`\n- Integrated `low_view` (<75%) tracker")

    with m_col2:
        with st.container(border=True):
            st.markdown("### 👨‍🎓 Student Roster (`2_Student`)")
            st.write("Student profiles, semester tracking, contact details, and department registries.")
            st.markdown("- Search by name pattern (`sname LIKE :term`)\n- Sort by name and filter by semester")

        with st.container(border=True):
            st.markdown("### 📋 Course Enrollment (`4_Enrollment`)")
            st.write("Map students to their respective semester subjects.")
            st.markdown("- Dynamic student & subject selection dropdowns\n- Unique constraint validation (no duplicate enrollments)")

        with st.container(border=True):
            st.markdown("### 🏖️ Leave Management (`6_Leave`)")
            st.write("Submit student leave requests, review pending applications, and manage leave balances.")
            st.markdown("- Approve leaves using stored procedure `proc_leaveapprov`\n- Trigger `trg_update_leave_balance` auto-adjusts quotas")

    with st.container(border=True):
        st.markdown("### 📊 Analytics & Insights (`7_Analytics`)")
        st.write("High-level academic analytics including subject-wise attendance ranking and defaulter monitoring (mirroring the PL/SQL cursor).")

else:
    st.warning("⚠️ **Oracle Database Disconnected**")
    st.info(
        "Could not connect to the Oracle database using the current settings.\n\n"
        "**To connect:**\n"
        "1. Open the **🔌 Database Connection** expander in the left sidebar.\n"
        "2. Provide your Oracle credentials (User, Password, and DSN e.g., `localhost:1521/ORCL`).\n"
        "3. Click **Save & Test**.\n"
        "4. Click **Run setup_db.sql** if you'd like to create and seed all tables, triggers, and procedures automatically."
    )

st.markdown("---")
st.caption("Powered by Oracle Database & Streamlit | Multi-Page Academic Suite")

