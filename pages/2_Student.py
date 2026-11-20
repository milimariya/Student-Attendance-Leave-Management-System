"""
Student Management Page.
Provides CRUD operations for Student entity and demonstrates query #2:
- Query #2: SELECT sname, sid FROM student WHERE sname LIKE 'A%'
"""

import streamlit as st
import pandas as pd
import db
import queries

st.set_page_config(page_title="Student Directory", page_icon="👨‍🎓", layout="wide")
db.render_sidebar()

st.title("👨‍🎓 Student Management")
st.markdown("Manage student profiles, departments, semesters, and CGPAs.")

tab_view, tab_add, tab_edit = st.tabs(["📋 Student Directory", "➕ Register Student", "✏️ Edit / Delete"])

# -----------------------------------------------------------------------------
# TAB 1: VIEW & FILTER
# -----------------------------------------------------------------------------
with tab_view:
    st.subheader("Student Directory")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_query = st.text_input("Search by Name (e.g. 'Alice' or 'A%')", placeholder="Type name or SQL pattern...")
    with col2:
        sort_by_name = st.checkbox("Sort by Name (A-Z)", value=True)
    with col3:
        sem_filter = st.selectbox("Semester", ["All Semesters"] + [f"Semester {i}" for i in range(1, 9)])

    # Determine query to run
    if search_query.strip():
        term = search_query.strip()
        # If user didn't specify wildcards, wrap with %
        if "%" not in term and "_" not in term:
            term = f"%{term}%"
        df = db.run_query(queries.SEARCH_STUDENTS_BY_NAME, {"term": term})
    elif sort_by_name:
        df = db.run_query(queries.GET_STUDENTS_ORDERED_BY_NAME)
    else:
        df = db.run_query(queries.GET_ALL_STUDENTS)

    # Filter semester in memory if requested
    if not df.empty and sem_filter != "All Semesters":
        target_sem = int(sem_filter.split()[1])
        df = df[df["sem"].map(db.parse_student_semester) == target_sem]

    if not df.empty:
        st.dataframe(
            df.rename(columns={
                "sid": "Student ID",
                "sname": "Full Name",
                "dept": "Department",
                "sem": "Semester",
                "cgpa": "CGPA"
            }),
            use_container_width=True,
            hide_index=True
        )
        st.info(f"Total students matched: **{len(df)}**")
    else:
        st.warning("No student records found matching the criteria.")

# -----------------------------------------------------------------------------
# TAB 2: REGISTER STUDENT
# -----------------------------------------------------------------------------
with tab_add:
    st.subheader("Register New Student")

    with st.form("form_add_student", clear_on_submit=True):
        col_id, col_name = st.columns(2)
        with col_id:
            s_id = st.text_input("Student ID (e.g. 37)", placeholder="37")
        with col_name:
            s_name = st.text_input("Full Name", placeholder="e.g. Maya Lin")

        col_dept, col_sem = st.columns(2)
        with col_dept:
            s_dept = st.selectbox("Department", [
                "Computer Science",
                "Electronics",
                "Information Technology",
                "Mechanical Engineering",
                "Civil Engineering",
                "Mathematics"
            ])
        with col_sem:
            s_sem = st.number_input("Current Semester (1 - 8)", min_value=1, max_value=8, value=1, step=1)
        s_cgpa = st.number_input("CGPA (0 - 10)", min_value=0.0, max_value=10.0, value=0.0, step=0.01, format="%.2f")

        init_balance = st.checkbox("Initialize Default Leave Balance (15 Days)", value=True)
        submitted = st.form_submit_button("Register Student", use_container_width=True)

        if submitted:
            if not s_id.strip() or not s_name.strip():
                st.error("Student ID and Name are required.")
            else:
                s_id_clean = s_id.strip().upper()
                params = {
                    "sid": s_id_clean,
                    "sname": s_name.strip(),
                    "dept": s_dept.strip(),
                    "sem": int(s_sem),
                    "cgpa": float(s_cgpa)
                }
                ok, _, err = db.run_dml(queries.INSERT_STUDENT, params)
                if ok:
                    if init_balance:
                        # Fetch next leave_balance ID
                        bid_df = db.run_query(queries.GET_NEXT_LEAVE_BAL_ID)
                        next_bid = int(bid_df.iloc[0]["next_id"]) if not bid_df.empty else 1
                        bal_params = {
                            "bid": next_bid,
                            "sid": s_id_clean,
                            "total_leave": 15,
                            "used_leave": 0,
                            "rem_leave": 15
                        }
                        db.run_dml(queries.INSERT_LEAVE_BALANCE, bal_params)

                    st.success(f"Student '{s_name}' ({s_id_clean}) registered successfully!")
                    st.rerun()

# -----------------------------------------------------------------------------
# TAB 3: EDIT / DELETE
# -----------------------------------------------------------------------------
with tab_edit:
    st.subheader("Update or Remove Student Record")
    students_df = db.run_query(queries.GET_ALL_STUDENTS)

    if students_df.empty:
        st.info("No students found in the database.")
    else:
        student_opts = {
            f"{row['sname']} ({row['sid']}) - Sem {row['sem']}": row['sid']
            for _, row in students_df.iterrows()
        }
        selected_label = st.selectbox("Select Student", list(student_opts.keys()))
        selected_sid = student_opts[selected_label]

        curr_df = db.run_query(queries.GET_STUDENT_BY_ID, {"sid": selected_sid})
        if not curr_df.empty:
            curr_row = curr_df.iloc[0]

            col_edit, col_del = st.columns([2, 1])

            with col_edit:
                st.markdown("#### Edit Profile Details")
                with st.form("form_edit_student"):
                    e_name = st.text_input("Full Name", value=str(curr_row["sname"]))

                    dept_list = [
                        "Computer Science",
                        "Electronics",
                        "Information Technology",
                        "Mechanical Engineering",
                        "Civil Engineering",
                        "Mathematics"
                    ]
                    cur_dept = str(curr_row["dept"])
                    dept_idx = dept_list.index(cur_dept) if cur_dept in dept_list else 0
                    e_dept = st.selectbox("Department", dept_list, index=dept_idx)

                    current_semester = db.parse_student_semester(curr_row["sem"])
                    if current_semester is None:
                        st.error(f"Cannot edit invalid semester value: {curr_row['sem']}")
                        current_semester = 1

                    e_sem = st.number_input(
                        "Semester",
                        min_value=1,
                        max_value=8,
                        value=current_semester
                    )
                    e_cgpa = st.number_input(
                        "CGPA",
                        min_value=0.0,
                        max_value=10.0,
                        value=float(curr_row["cgpa"]) if pd.notnull(curr_row["cgpa"]) else 0.0,
                        step=0.01,
                        format="%.2f"
                    )

                    if st.form_submit_button("Update Student Profile", use_container_width=True):
                        update_params = {
                            "sid": selected_sid,
                            "sname": e_name.strip(),
                            "dept": e_dept.strip(),
                            "sem": int(e_sem),
                            "cgpa": float(e_cgpa)
                        }
                        ok, _, _ = db.run_dml(queries.UPDATE_STUDENT, update_params)
                        if ok:
                            st.success(f"Profile for {e_name} updated successfully!")
                            st.rerun()

            with col_del:
                st.markdown("#### Delete Student")
                st.warning(
                    f"Deleting student **{curr_row['sname']}** will fail if attendance, enrollment, "
                    f"or leave records are associated with this student ID."
                )
                confirm_del = st.checkbox("Confirm permanent deletion", key="chk_del_stu")
                if st.button("Delete Student", type="primary", use_container_width=True, disabled=not confirm_del):
                    ok, _, err = db.run_dml(queries.DELETE_STUDENT, {"sid": selected_sid})
                    if ok:
                        st.success(f"Student {selected_sid} removed from database.")
                        st.rerun()
                    else:
                        st.error(f"Cannot delete student: {err}")
