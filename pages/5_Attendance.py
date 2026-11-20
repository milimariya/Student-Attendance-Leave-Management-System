"""
Attendance Management Page.
Core feature module supporting:
- Daily batch and single attendance marking
- View attendance records with date and course filters
- PL/SQL Function call: attfunction(p_sid, p_subid)
- Low attendance tracking via low_view and the project JOIN query (< 75%)
- Edit / Delete attendance records
"""

import streamlit as st
import pandas as pd
from datetime import date
import db
import queries

st.set_page_config(page_title="Attendance Portal", page_icon="📝", layout="wide")
db.render_sidebar()

st.title("📝 Attendance Management")
st.markdown("Record daily attendance, query percentage metrics, and identify students below threshold.")

tab_mark, tab_view, tab_calc, tab_low, tab_edit = st.tabs([
    "✍️ Mark Attendance",
    "📋 Attendance Records",
    "🎯 Per-Student Calculator",
    "⚠️ Low Attendance (<75%)",
    "✏️ Edit / Delete"
])

# -----------------------------------------------------------------------------
# TAB 1: MARK ATTENDANCE
# -----------------------------------------------------------------------------
with tab_mark:
    st.subheader("Mark Daily Class Attendance")

    sub_df = db.run_query(queries.GET_ALL_SUBJECTS)
    if sub_df.empty:
        st.warning("No subjects registered yet. Please add subjects first.")
    else:
        sub_opts = {
            f"{row['subid']} - {row['subname']} (Sem {row['sem']})": row['subid']
            for _, row in sub_df.iterrows()
        }

        col_sub, col_dt = st.columns([2, 1])
        with col_sub:
            selected_sub_label = st.selectbox("Select Subject", list(sub_opts.keys()), key="att_mark_sub")
            selected_subid = sub_opts[selected_sub_label]
        with col_dt:
            att_date = st.date_input("Attendance Date", value=date.today(), key="att_mark_date")

        # Fetch students enrolled in this subject
        enrolled_df = db.run_query(queries.GET_STUDENTS_ENROLLED_IN_SUBJECT, {"subid": selected_subid})

        if enrolled_df.empty:
            st.info(f"No students are enrolled in **{selected_subid}**. Please enroll students on the Course Enrollment page.")
        else:
            st.markdown(f"**Enrolled Students ({len(enrolled_df)})** — Mark Present/Absent for `{att_date}`:")

            # Form for batch marking
            with st.form("form_batch_attendance"):
                attendance_states = {}

                # Table header
                h1, h2, h3, h4 = st.columns([1, 2, 2, 2])
                h1.markdown("**Student ID**")
                h2.markdown("**Name**")
                h3.markdown("**Department**")
                h4.markdown("**Status**")

                for _, stu in enrolled_df.iterrows():
                    sid = stu["sid"]
                    sname = stu["sname"]
                    c1, c2, c3, c4 = st.columns([1, 2, 2, 2])
                    c1.write(f"`{sid}`")
                    c2.write(sname)
                    c3.write(stu["dept"])
                    # Toggle or selectbox
                    status = c4.radio(
                        f"Status for {sid}",
                        options=["present", "absent"],
                        index=0,
                        horizontal=True,
                        label_visibility="collapsed",
                        key=f"status_{sid}"
                    )
                    attendance_states[sid] = status

                submit_batch = st.form_submit_button("Submit Attendance", use_container_width=True)

                if submit_batch:
                    # Get base next ID
                    aid_df = db.run_query(queries.GET_NEXT_ATTENDANCE_ID)
                    current_aid = int(aid_df.iloc[0]["next_id"]) if not aid_df.empty else 1

                    success_count = 0
                    skip_count = 0

                    for sid, status in attendance_states.items():
                        # Check duplicate for the same date
                        chk = db.run_query(queries.CHECK_ATTENDANCE_EXISTS, {
                            "sid": sid,
                            "subid": selected_subid,
                            "adate": att_date
                        })
                        if not chk.empty and chk.iloc[0]["cnt"] > 0:
                            skip_count += 1
                        else:
                            ok, _, _ = db.run_dml(queries.INSERT_ATTENDANCE, {
                                "aid": current_aid,
                                "sid": sid,
                                "subid": selected_subid,
                                "adate": att_date,
                                "status": status
                            })
                            if ok:
                                current_aid += 1
                                success_count += 1

                    if success_count > 0:
                        st.success(f"Recorded attendance for **{success_count}** student(s).")
                    if skip_count > 0:
                        st.warning(f"Skipped **{skip_count}** student(s) because attendance was already marked for {att_date}.")
                    if success_count > 0:
                        st.rerun()

# -----------------------------------------------------------------------------
# TAB 2: VIEW ATTENDANCE RECORDS
# -----------------------------------------------------------------------------
with tab_view:
    st.subheader("Attendance Log Archive")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        sub_list_df = db.run_query(queries.GET_ALL_SUBJECTS)
        subject_filter_opts = ["All Subjects"] + (list(sub_list_df["subid"].unique()) if not sub_list_df.empty else [])
        filter_sub = st.selectbox("Filter Subject", subject_filter_opts, key="filter_att_sub")
    with col_f2:
        filter_date_toggle = st.checkbox("Filter by Date", value=False)
        selected_filter_date = st.date_input("Date", value=date.today(), key="filter_att_date") if filter_date_toggle else None

    # Fetch logs
    param_sub = filter_sub if filter_sub != "All Subjects" else None
    param_dt = selected_filter_date if filter_date_toggle else None

    logs_df = db.run_query(queries.GET_ATTENDANCE_FILTERED, {"subid": param_sub, "adate": param_dt})

    if not logs_df.empty:
        if "adate" in logs_df.columns:
            logs_df["adate"] = pd.to_datetime(logs_df["adate"]).dt.strftime("%Y-%m-%d")

        st.dataframe(
            logs_df.rename(columns={
                "aid": "Log ID",
                "sid": "Student ID",
                "student_name": "Student Name",
                "subid": "Subject Code",
                "subject_name": "Subject Title",
                "adate": "Session Date",
                "status": "Attendance Status"
            }),
            use_container_width=True,
            hide_index=True
        )
        st.info(f"Total matching attendance entries: **{len(logs_df)}**")
    else:
        st.warning("No attendance records found.")

# -----------------------------------------------------------------------------
# TAB 3: PER-STUDENT CALCULATOR (Calls attfunction)
# -----------------------------------------------------------------------------
with tab_calc:
    st.subheader("🎯 Student Attendance Percentage Lookup")
    st.caption("Executes Oracle PL/SQL function `attfunction(p_sid, p_subid)`")

    stu_df = db.run_query(queries.GET_ALL_STUDENTS)
    sub_df = db.run_query(queries.GET_ALL_SUBJECTS)

    if stu_df.empty or sub_df.empty:
        st.warning("Please ensure students and subjects are created.")
    else:
        stu_opts = {f"{r['sname']} ({r['sid']})": r['sid'] for _, r in stu_df.iterrows()}
        sub_opts = {f"{r['subid']} - {r['subname']}": r['subid'] for _, r in sub_df.iterrows()}

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            calc_stu_label = st.selectbox("Select Student", list(stu_opts.keys()), key="calc_stu")
            calc_sid = stu_opts[calc_stu_label]
        with col_c2:
            calc_sub_label = st.selectbox("Select Subject", list(sub_opts.keys()), key="calc_sub")
            calc_subid = sub_opts[calc_sub_label]

        if st.button("Calculate Attendance %", type="primary"):
            # Call PL/SQL Function
            func_df = db.run_query(queries.CALL_ATTFUNCTION, {"sid": calc_sid, "subid": calc_subid})
            if not func_df.empty:
                pct = float(func_df.iloc[0]["attendance_pct"])
                col_m1, col_m2 = st.columns([1, 2])
                with col_m1:
                    st.metric(
                        label="Calculated Attendance",
                        value=f"{pct:.1f}%",
                        delta="Eligible for Exams" if pct >= 75 else "⚠️ Shortage (<75%)",
                        delta_color="normal" if pct >= 75 else "inverse"
                    )
                with col_c2:
                    st.progress(min(pct / 100.0, 1.0))
                    if pct < 75:
                        st.error(f"Student {calc_sid} has attendance below the 75% threshold in {calc_subid}!")
                    else:
                        st.success(f"Student {calc_sid} satisfies minimum attendance requirements.")

# -----------------------------------------------------------------------------
# TAB 4: LOW ATTENDANCE VIEW (< 75%)
# -----------------------------------------------------------------------------
with tab_low:
    st.subheader("⚠️ Low Attendance Report (< 75%)")
    st.markdown("Directly maps to Oracle DB view `low_view` and the subject attendance JOIN query.")

    low_df = db.run_query(queries.GET_LOW_ATTENDANCE_JOIN)

    if not low_df.empty:
        st.warning(f"**{len(low_df)}** student-subject instances are currently below the required 75% attendance threshold.")
        st.dataframe(
            low_df.rename(columns={
                "sid": "Student ID",
                "sname": "Student Name",
                "subid": "Subject Code",
                "attendance_percentage": "Attendance Percentage (%)"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("🎉 All students currently maintain 75% or higher attendance across all subjects!")

# -----------------------------------------------------------------------------
# TAB 5: EDIT / DELETE
# -----------------------------------------------------------------------------
with tab_edit:
    st.subheader("Modify or Delete Attendance Record")

    all_att_df = db.run_query(queries.GET_ALL_ATTENDANCE)

    if all_att_df.empty:
        st.info("No attendance records to modify.")
    else:
        # Show recent 50
        opts = {
            f"Log #{row['aid']} | {row['student_name']} ({row['sid']}) | {row['subid']} | {pd.to_datetime(row['adate']).strftime('%Y-%m-%d')} | [{row['status'].upper()}]": row['aid']
            for _, row in all_att_df.head(50).iterrows()
        }
        selected_log_label = st.selectbox("Select Attendance Entry", list(opts.keys()))
        selected_aid = opts[selected_log_label]

        curr_rec = all_att_df[all_att_df["aid"] == selected_aid].iloc[0]

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            st.markdown("#### Toggle Status")
            current_status = curr_rec["status"].lower()
            new_status = st.radio(
                "Update Status",
                ["present", "absent"],
                index=0 if current_status == "present" else 1,
                horizontal=True
            )
            if st.button("Save Updated Status"):
                ok, _, _ = db.run_dml(queries.UPDATE_ATTENDANCE, {"aid": int(selected_aid), "status": new_status})
                if ok:
                    st.success(f"Status updated to '{new_status}'!")
                    st.rerun()

        with col_e2:
            st.markdown("#### Delete Record")
            st.caption("Remove this single attendance log entry.")
            confirm_att_del = st.checkbox("Confirm delete record", key="chk_del_att_rec")
            if st.button("Delete Log", type="primary", disabled=not confirm_att_del):
                ok, _, _ = db.run_dml(queries.DELETE_ATTENDANCE, {"aid": int(selected_aid)})
                if ok:
                    st.success(f"Attendance log #{selected_aid} deleted.")
                    st.rerun()

