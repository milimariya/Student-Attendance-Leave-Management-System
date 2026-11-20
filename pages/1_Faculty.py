"""
Faculty Management Page.
Provides CRUD operations for Faculty entity and demonstrates basic queries:
- Query #1: SELECT fname, fid FROM faculty WHERE fid > :min_id
- Query #3: SELECT fname FROM faculty ORDER BY fname ASC
"""

import streamlit as st
import pandas as pd
import db
import queries

st.set_page_config(page_title="Faculty Directory", page_icon="👨‍🏫", layout="wide")
db.render_sidebar()

st.title("👨‍🏫 Faculty Management")
st.markdown("View, register, update, and manage academic faculty members.")

tab_view, tab_add, tab_edit = st.tabs(["📋 View & Filter", "➕ Add Faculty", "✏️ Edit / Delete"])

# -----------------------------------------------------------------------------
# TAB 1: VIEW & FILTER
# -----------------------------------------------------------------------------
with tab_view:
    st.subheader("Faculty Directory")

    col1, col2 = st.columns([1, 1])
    with col1:
        sort_by_name = st.checkbox("Sort by Name (A to Z)", help="Runs: SELECT fname FROM faculty ORDER BY fname ASC")
    with col2:
        filter_fid = st.checkbox("Filter by Minimum FID", help="Runs: SELECT fname, fid FROM faculty WHERE fid > :min_id")
        min_fid_val = st.number_input("Minimum FID Threshold", value=105, step=1) if filter_fid else 0

    if filter_fid:
        df = db.run_query(queries.GET_FACULTY_FILTER_MIN_ID, {"min_id": min_fid_val})
        st.caption(f"Showing faculty members with ID > {min_fid_val}")
    elif sort_by_name:
        df = db.run_query(queries.GET_FACULTY_ORDERED_BY_NAME)
        st.caption("Showing faculty ordered alphabetically by name")
    else:
        df = db.run_query(queries.GET_ALL_FACULTY)

    if not df.empty:
        st.dataframe(
            df.rename(columns={
                "fid": "Faculty ID",
                "fname": "Full Name",
                "email": "Email Address",
                "dept": "Department"
            }),
            use_container_width=True,
            hide_index=True
        )
        st.info(f"Total faculty members found: **{len(df)}**")
    else:
        st.warning("No faculty records found.")

# -----------------------------------------------------------------------------
# TAB 2: ADD FACULTY
# -----------------------------------------------------------------------------
with tab_add:
    st.subheader("Register New Faculty")

    # Fetch suggested next ID
    next_id_df = db.run_query(queries.GET_NEXT_FACULTY_ID)
    suggested_id = int(next_id_df.iloc[0]["next_id"]) if not next_id_df.empty else 101

    with st.form("form_add_faculty", clear_on_submit=True):
        f_id = st.number_input("Faculty ID (FID)", value=suggested_id, step=1)
        f_name = st.text_input("Full Name", placeholder="e.g. Dr. Ada Lovelace")
        f_email = st.text_input("Email", placeholder="e.g. ada.lovelace@univ.edu")
        f_dept = st.selectbox("Department", [
            "Computer Science",
            "Electronics",
            "Mathematics",
            "Physics",
            "Information Technology",
            "Mechanical Engineering"
        ])
        submitted = st.form_submit_button("Register Faculty", use_container_width=True)

        if submitted:
            if not f_name or not f_email:
                st.error("Please provide both Full Name and Email.")
            else:
                params = {
                    "fid": int(f_id),
                    "fname": f_name.strip(),
                    "email": f_email.strip(),
                    "dept": f_dept.strip()
                }
                success, rowcount, err = db.run_dml(queries.INSERT_FACULTY, params)
                if success:
                    st.success(f"Faculty '{f_name}' (ID: {f_id}) successfully registered!")
                    st.rerun()

# -----------------------------------------------------------------------------
# TAB 3: EDIT / DELETE
# -----------------------------------------------------------------------------
with tab_edit:
    st.subheader("Update or Remove Faculty Record")
    faculty_list_df = db.run_query(queries.GET_ALL_FACULTY)

    if faculty_list_df.empty:
        st.info("No faculty records available to modify.")
    else:
        # Build options dictionary
        faculty_options = {
            f"{row['fname']} (ID: {row['fid']})": row['fid']
            for _, row in faculty_list_df.iterrows()
        }
        selected_label = st.selectbox("Select Faculty Member", list(faculty_options.keys()))
        selected_fid = faculty_options[selected_label]

        # Fetch current details
        curr_df = db.run_query(queries.GET_FACULTY_BY_ID, {"fid": selected_fid})
        if not curr_df.empty:
            curr_row = curr_df.iloc[0]

            col_edit, col_del = st.columns([2, 1])

            with col_edit:
                st.markdown("#### Edit Details")
                with st.form("form_edit_faculty"):
                    e_name = st.text_input("Full Name", value=str(curr_row["fname"]))
                    e_email = st.text_input("Email", value=str(curr_row["email"]))
                    dept_list = [
                        "Computer Science",
                        "Electronics",
                        "Mathematics",
                        "Physics",
                        "Information Technology",
                        "Mechanical Engineering"
                    ]
                    current_dept = str(curr_row["dept"])
                    dept_idx = dept_list.index(current_dept) if current_dept in dept_list else 0
                    e_dept = st.selectbox("Department", dept_list, index=dept_idx)

                    update_btn = st.form_submit_button("Save Changes", use_container_width=True)
                    if update_btn:
                        update_params = {
                            "fid": int(selected_fid),
                            "fname": e_name.strip(),
                            "email": e_email.strip(),
                            "dept": e_dept.strip()
                        }
                        ok, _, _ = db.run_dml(queries.UPDATE_FACULTY, update_params)
                        if ok:
                            st.success("Faculty details updated successfully!")
                            st.rerun()

            with col_del:
                st.markdown("#### Delete Faculty")
                st.warning(
                    f"Deleting **{curr_row['fname']}** will fail if subjects are currently linked to this faculty."
                )
                confirm_delete = st.checkbox("I confirm I want to delete this faculty member", key="chk_del_fac")
                if st.button("Delete Faculty Record", type="primary", use_container_width=True, disabled=not confirm_delete):
                    ok, _, err = db.run_dml(queries.DELETE_FACULTY, {"fid": int(selected_fid)})
                    if ok:
                        st.success(f"Faculty record (ID: {selected_fid}) deleted.")
                        st.rerun()
                    else:
                        st.error(f"Cannot delete: {err}")

