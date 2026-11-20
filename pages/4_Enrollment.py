"""
Enrollment Management Page.
Maps Students to Subjects with unique constraint enforcement (sid, subid).
"""

import streamlit as st
import pandas as pd
from datetime import date
import db
import queries

st.set_page_config(page_title="Course Enrollment", page_icon="📋", layout="wide")
db.render_sidebar()

st.title("📋 Course Enrollment")
st.markdown("Manage student subject enrollments and view active class rosters.")

tab_view, tab_enroll, tab_unenroll = st.tabs(["📋 View Enrollments", "➕ Enroll Student", "🗑️ Unenroll Student"])

# -----------------------------------------------------------------------------
# TAB 1: VIEW ENROLLMENTS
# -----------------------------------------------------------------------------
with tab_view:
    st.subheader("Active Course Enrollments")

    enr_df = db.run_query(queries.GET_ALL_ENROLLMENTS)

    if not enr_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            subject_options = ["All Subjects"] + sorted(list(enr_df["subject_name"].unique()))
            selected_sub = st.selectbox("Filter by Subject", subject_options)
        with col2:
            student_search = st.text_input("Filter by Student Name or ID", placeholder="e.g. Alice, S001")

        filtered_df = enr_df.copy()
        if selected_sub != "All Subjects":
            filtered_df = filtered_df[filtered_df["subject_name"] == selected_sub]

        if student_search.strip():
            kw = student_search.strip().lower()
            filtered_df = filtered_df[
                filtered_df["sid"].str.lower().str.contains(kw, na=False) |
                filtered_df["student_name"].str.lower().str.contains(kw, na=False)
            ]

        # Format dates cleanly
        if "edate" in filtered_df.columns:
            filtered_df["edate"] = pd.to_datetime(filtered_df["edate"]).dt.strftime("%Y-%m-%d")

        st.dataframe(
            filtered_df.rename(columns={
                "eid": "Enrollment ID",
                "sid": "Student ID",
                "student_name": "Student Name",
                "subid": "Subject Code",
                "subject_name": "Subject Title",
                "edate": "Enrollment Date"
            }),
            use_container_width=True,
            hide_index=True
        )
        st.info(f"Showing **{len(filtered_df)}** enrollment records.")
    else:
        st.warning("No course enrollments found.")

# -----------------------------------------------------------------------------
# TAB 2: ENROLL STUDENT
# -----------------------------------------------------------------------------
with tab_enroll:
    st.subheader("Enroll Student in a Subject")

    stu_df = db.run_query(queries.GET_ALL_STUDENTS)
    sub_df = db.run_query(queries.GET_ALL_SUBJECTS)

    if stu_df.empty or sub_df.empty:
        st.error("You need both registered Students and Subjects to create an enrollment.")
    else:
        stu_opts = {
            f"{row['sname']} ({row['sid']}) - Sem {row['sem']}": row['sid']
            for _, row in stu_df.iterrows()
        }

        sel_stu_label = st.selectbox("Select Student", list(stu_opts.keys()))
        sid_val = stu_opts[sel_stu_label]
        student_sem = db.parse_student_semester(
            stu_df.loc[stu_df["sid"] == sid_val, "sem"].iloc[0]
        )
        semester_subjects = sub_df.iloc[0:0]

        if student_sem is None:
            st.error(f"Student {sid_val} has an invalid semester and cannot be enrolled.")
        else:
            subject_semesters = sub_df["sem"].map(db.parse_student_semester)
            semester_subjects = sub_df[subject_semesters == student_sem]

        if student_sem is not None and semester_subjects.empty:
            st.warning(
                f"No subjects are available for semester {student_sem}. "
                "Add a subject for this semester before enrolling the student."
            )
        elif student_sem is not None:
            sub_opts = {
                f"{row['subid']} - {row['subname']} (Sem {row['sem']})": row['subid']
                for _, row in semester_subjects.iterrows()
            }
            sel_sub_label = st.selectbox("Select Subject", list(sub_opts.keys()))
            subid_val = sub_opts[sel_sub_label]

            with st.form("form_enroll_student", clear_on_submit=True):
                enroll_date = st.date_input("Enrollment Date", value=date.today())
                submitted = st.form_submit_button("Enroll Student", use_container_width=True)

            if submitted:
                # Check duplicate
                check_df = db.run_query(queries.CHECK_ENROLLMENT_EXISTS, {"sid": sid_val, "subid": subid_val})
                if not check_df.empty and check_df.iloc[0]["cnt"] > 0:
                    st.warning(f"Student {sid_val} is already enrolled in {subid_val}!")
                else:
                    # Get next ID
                    eid_df = db.run_query(queries.GET_NEXT_ENROLLMENT_ID)
                    next_eid = int(eid_df.iloc[0]["next_id"]) if not eid_df.empty else 1

                    params = {
                        "eid": next_eid,
                        "sid": sid_val,
                        "subid": subid_val,
                        "edate": enroll_date
                    }
                    ok, _, err = db.run_dml(queries.INSERT_ENROLLMENT, params)
                    if ok:
                        st.success(f"Successfully enrolled {sid_val} in {subid_val}!")
                        st.rerun()

# -----------------------------------------------------------------------------
# TAB 3: UNENROLL
# -----------------------------------------------------------------------------
with tab_unenroll:
    st.subheader("Remove Enrollment Record")

    enr_data = db.run_query(queries.GET_ALL_ENROLLMENTS)
    if enr_data.empty:
        st.info("No enrollments to remove.")
    else:
        del_opts = {
            f"EID {row['eid']}: {row['student_name']} ({row['sid']}) → {row['subject_name']} ({row['subid']})": row['eid']
            for _, row in enr_data.iterrows()
        }
        selected_del_label = st.selectbox("Select Enrollment to Cancel", list(del_opts.keys()))
        selected_eid = del_opts[selected_del_label]

        confirm_unenroll = st.checkbox("Confirm unenrollment", key="chk_del_enr")
        if st.button("Unenroll Student", type="primary", disabled=not confirm_unenroll):
            ok, _, err = db.run_dml(queries.DELETE_ENROLLMENT, {"eid": int(selected_eid)})
            if ok:
                st.success(f"Enrollment {selected_eid} successfully removed.")
                st.rerun()
            else:
                st.error(f"Failed to unenroll: {err}")
