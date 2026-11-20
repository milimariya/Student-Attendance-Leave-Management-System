"""
Subject Management Page.
Provides CRUD operations for Course / Subject entities linked with Faculty Foreign Keys.
"""

import streamlit as st
import pandas as pd
import db
import queries

st.set_page_config(page_title="Subject Catalog", page_icon="📚", layout="wide")
db.render_sidebar()

st.title("📚 Subject Management")
st.markdown("Configure courses, credit allotments, semesters, and assign lead faculty.")

tab_view, tab_add, tab_edit = st.tabs(["📋 Subject Catalog", "➕ Add Subject", "✏️ Edit / Delete"])

# -----------------------------------------------------------------------------
# TAB 1: VIEW SUBJECTS
# -----------------------------------------------------------------------------
with tab_view:
    st.subheader("Curriculum & Course Catalog")

    col1, col2 = st.columns(2)
    with col1:
        sem_filter = st.selectbox("Filter by Semester", ["All"] + [f"Semester {i}" for i in range(1, 9)])
    with col2:
        search_kw = st.text_input("Search Course by Name or Code", placeholder="e.g. Database, CS501")

    df = db.run_query(queries.GET_ALL_SUBJECTS)

    if not df.empty:
        if sem_filter != "All":
            target_sem = int(sem_filter.split()[1])
            df = df[df["sem"] == target_sem]

        if search_kw.strip():
            kw = search_kw.strip().lower()
            df = df[
                df["subid"].str.lower().str.contains(kw, na=False) |
                df["subname"].str.lower().str.contains(kw, na=False)
            ]

        st.dataframe(
            df.rename(columns={
                "subid": "Subject Code",
                "subname": "Subject Title",
                "credits": "Credits",
                "sem": "Semester",
                "fid": "Faculty ID",
                "faculty_name": "Assigned Faculty"
            }),
            use_container_width=True,
            hide_index=True
        )
        st.info(f"Total subjects displayed: **{len(df)}**")
    else:
        st.warning("No subjects found in the database.")

# -----------------------------------------------------------------------------
# TAB 2: ADD SUBJECT
# -----------------------------------------------------------------------------
with tab_add:
    st.subheader("Add New Subject")

    # Fetch faculty members for dropdown
    fac_df = db.run_query(queries.GET_ALL_FACULTY)
    fac_opts = {}
    if not fac_df.empty:
        fac_opts = {
            f"{row['fname']} ({row['dept']}) [ID: {row['fid']}]": int(row['fid'])
            for _, row in fac_df.iterrows()
        }

    with st.form("form_add_subject", clear_on_submit=True):
        col_id, col_name = st.columns([1, 2])
        with col_id:
            sub_id = st.text_input("Subject Code (e.g. CS501)", placeholder="CS501")
        with col_name:
            sub_name = st.text_input("Subject Name", placeholder="e.g. Database Management Systems")

        col_cred, col_sem, col_fac = st.columns([1, 1, 2])
        with col_cred:
            credits = st.number_input("Credits ( > 0 )", min_value=1, max_value=10, value=4, step=1)
        with col_sem:
            sem = st.number_input("Semester (1 - 8)", min_value=1, max_value=8, value=5, step=1)
        with col_fac:
            selected_fac_label = st.selectbox(
                "Assign Faculty Lead",
                options=["-- None --"] + list(fac_opts.keys())
            )

        submitted = st.form_submit_button("Create Subject", use_container_width=True)

        if submitted:
            if not sub_id.strip() or not sub_name.strip():
                st.error("Please provide both Subject Code and Name.")
            else:
                fid_val = fac_opts.get(selected_fac_label) if selected_fac_label != "-- None --" else None
                params = {
                    "subid": sub_id.strip().upper(),
                    "subname": sub_name.strip(),
                    "credits": int(credits),
                    "sem": int(sem),
                    "fid": fid_val
                }
                ok, _, err = db.run_dml(queries.INSERT_SUBJECT, params)
                if ok:
                    st.success(f"Subject '{sub_name}' ({sub_id.upper()}) added successfully!")
                    st.rerun()

# -----------------------------------------------------------------------------
# TAB 3: EDIT / DELETE
# -----------------------------------------------------------------------------
with tab_edit:
    st.subheader("Edit or Remove Subject")
    subjects_df = db.run_query(queries.GET_ALL_SUBJECTS)

    if subjects_df.empty:
        st.info("No subjects available.")
    else:
        subject_opts = {
            f"{row['subid']} - {row['subname']} (Sem {row['sem']})": row['subid']
            for _, row in subjects_df.iterrows()
        }
        selected_sub_label = st.selectbox("Select Subject", list(subject_opts.keys()))
        selected_subid = subject_opts[selected_sub_label]

        sub_detail_df = db.run_query(queries.GET_SUBJECT_BY_ID, {"subid": selected_subid})
        if not sub_detail_df.empty:
            curr = sub_detail_df.iloc[0]

            col_edit, col_del = st.columns([2, 1])

            with col_edit:
                st.markdown("#### Edit Subject Information")
                fac_df = db.run_query(queries.GET_ALL_FACULTY)
                fac_opts = {
                    f"{row['fname']} ({row['dept']}) [ID: {row['fid']}]": int(row['fid'])
                    for _, row in fac_df.iterrows()
                }

                with st.form("form_edit_subject"):
                    e_subname = st.text_input("Subject Title", value=str(curr["subname"]))
                    e_credits = st.number_input("Credits", min_value=1, max_value=10, value=int(curr["credits"]))
                    e_sem = st.number_input("Semester", min_value=1, max_value=8, value=int(curr["sem"]))

                    curr_fid = int(curr["fid"]) if pd.notnull(curr["fid"]) else None
                    fac_keys = list(fac_opts.keys())
                    match_idx = 0
                    if curr_fid:
                        for idx, k in enumerate(fac_keys):
                            if fac_opts[k] == curr_fid:
                                match_idx = idx + 1
                                break

                    e_fac_label = st.selectbox(
                        "Assigned Faculty",
                        ["-- None --"] + fac_keys,
                        index=match_idx
                    )

                    if st.form_submit_button("Update Subject", use_container_width=True):
                        new_fid = fac_opts.get(e_fac_label) if e_fac_label != "-- None --" else None
                        update_params = {
                            "subid": selected_subid,
                            "subname": e_subname.strip(),
                            "credits": int(e_credits),
                            "sem": int(e_sem),
                            "fid": new_fid
                        }
                        ok, _, _ = db.run_dml(queries.UPDATE_SUBJECT, update_params)
                        if ok:
                            st.success(f"Subject {selected_subid} updated successfully!")
                            st.rerun()

            with col_del:
                st.markdown("#### Delete Subject")
                st.warning("Deleting this subject will fail if students are enrolled or attendance exists.")
                confirm_del = st.checkbox("I confirm subject deletion", key="chk_del_sub")
                if st.button("Delete Subject", type="primary", use_container_width=True, disabled=not confirm_del):
                    ok, _, err = db.run_dml(queries.DELETE_SUBJECT, {"subid": selected_subid})
                    if ok:
                        st.success(f"Subject {selected_subid} deleted.")
                        st.rerun()
                    else:
                        st.error(f"Cannot delete subject: {err}")

