"""
Leave Management Page.
Integrates:
- Leave applications with pending / approved / rejected lifecycle
- PL/SQL Stored Procedure: proc_leaveapprov(p_lid)
- Oracle Trigger: trg_update_leave_balance (auto-decrements remaining leave)
- Leave Balances tracking per student
"""

import streamlit as st
import pandas as pd
from datetime import date
import db
import queries

st.set_page_config(page_title="Leave Management", page_icon="🏖️", layout="wide")
db.render_sidebar()

st.title("🏖️ Student Leave Management")
st.markdown("Submit leave applications, process approvals via PL/SQL procedures, and track leave balances.")

tab_pending, tab_apply, tab_balance, tab_history = st.tabs([
    "⏳ Pending Approvals",
    "✍️ Apply for Leave",
    "💼 Leave Balances",
    "📜 Application History"
])

# -----------------------------------------------------------------------------
# TAB 1: PENDING APPROVALS
# -----------------------------------------------------------------------------
with tab_pending:
    st.subheader("Pending Leave Requests")
    st.caption("Approving calls `proc_leaveapprov(lid)` which triggers `trg_update_leave_balance`.")

    pending_df = db.run_query(queries.GET_PENDING_LEAVE_APPLICATIONS)

    if pending_df.empty:
        st.success("✨ No pending leave applications at this time!")
    else:
        # Display table
        display_df = pending_df.copy()
        if "ldate" in display_df.columns:
            display_df["ldate"] = pd.to_datetime(display_df["ldate"]).dt.strftime("%Y-%m-%d")

        st.dataframe(
            display_df.rename(columns={
                "lid": "Application ID",
                "sid": "Student ID",
                "student_name": "Student Name",
                "dept": "Department",
                "ldate": "Leave Date",
                "reason": "Reason",
                "lstatus": "Status",
                "rem_leave": "Remaining Balance"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
        st.markdown("#### Process Application")

        req_opts = {
            f"App #{row['lid']}: {row['student_name']} ({row['sid']}) on {row['ldate']} [Rem: {row['rem_leave'] or 0} days]": row['lid']
            for _, row in display_df.iterrows()
        }

        col_sel, col_act1, col_act2 = st.columns([3, 1, 1])
        with col_sel:
            sel_req_label = st.selectbox("Select Leave Application", list(req_opts.keys()))
            sel_lid = int(req_opts[sel_req_label])

        with col_act1:
            st.write("")
            st.write("")
            if st.button("✅ Approve Request", type="primary", use_container_width=True):
                # Call PL/SQL stored procedure proc_leaveapprov
                with st.spinner("Executing proc_leaveapprov..."):
                    ok, err = db.call_proc("proc_leaveapprov", [sel_lid])
                    if ok:
                        st.success(f"Leave #{sel_lid} approved! Trigger updated student leave balance.")
                        st.rerun()
                    else:
                        st.error(f"Approval failed: {err}")

        with col_act2:
            st.write("")
            st.write("")
            if st.button("❌ Reject Request", use_container_width=True):
                ok, _, err = db.run_dml(queries.REJECT_LEAVE_APPLICATION, {"lid": sel_lid})
                if ok:
                    st.info(f"Leave #{sel_lid} rejected.")
                    st.rerun()
                else:
                    st.error(f"Rejection failed: {err}")

# -----------------------------------------------------------------------------
# TAB 2: APPLY FOR LEAVE
# -----------------------------------------------------------------------------
with tab_apply:
    st.subheader("Submit New Leave Application")

    stu_df = db.run_query(queries.GET_ALL_STUDENTS)

    if stu_df.empty:
        st.warning("Please register students first.")
    else:
        stu_opts = {f"{r['sname']} ({r['sid']})": r['sid'] for _, r in stu_df.iterrows()}

        with st.form("form_apply_leave", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                sel_stu_label = st.selectbox("Select Student", list(stu_opts.keys()))
                sel_sid = stu_opts[sel_stu_label]
            with col2:
                leave_dt = st.date_input("Requested Leave Date", value=date.today())

            # Check remaining balance
            bal_df = db.run_query(queries.GET_LEAVE_BALANCE_BY_STUDENT, {"sid": sel_sid})
            rem_bal = bal_df.iloc[0]["rem_leave"] if not bal_df.empty else 0
            st.caption(f"Current remaining leave balance for `{sel_sid}`: **{rem_bal}** day(s)")

            reason = st.text_area("Reason for Leave", placeholder="e.g. Medical illness, family emergency, conference...")

            submit_apply = st.form_submit_button("Submit Leave Application", use_container_width=True)

            if submit_apply:
                if not reason.strip():
                    st.error("Please provide a reason for the leave application.")
                else:
                    lid_df = db.run_query(queries.GET_NEXT_LEAVE_APP_ID)
                    next_lid = int(lid_df.iloc[0]["next_id"]) if not lid_df.empty else 1

                    params = {
                        "lid": next_lid,
                        "sid": sel_sid,
                        "ldate": leave_dt,
                        "reason": reason.strip()
                    }
                    ok, _, err = db.run_dml(queries.INSERT_LEAVE_APPLICATION, params)
                    if ok:
                        st.success(f"Leave application #{next_lid} submitted for student {sel_sid}!")
                        st.rerun()

# -----------------------------------------------------------------------------
# TAB 3: LEAVE BALANCES
# -----------------------------------------------------------------------------
with tab_balance:
    st.subheader("Student Leave Balance Ledger")

    balances_df = db.run_query(queries.GET_ALL_LEAVE_BALANCES)

    if balances_df.empty:
        st.info("No leave balances found.")
    else:
        st.dataframe(
            balances_df.rename(columns={
                "bid": "Balance ID",
                "sid": "Student ID",
                "student_name": "Student Name",
                "dept": "Department",
                "total_leave": "Total Quota",
                "used_leave": "Days Used",
                "rem_leave": "Days Remaining"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
        with st.expander("⚙️ Manual Balance Adjustment / Initialize"):
            with st.form("form_update_balance"):
                adj_opts = {f"{r['student_name']} ({r['sid']})": r['sid'] for _, r in balances_df.iterrows()}
                adj_stu_label = st.selectbox("Select Student", list(adj_opts.keys()))
                adj_sid = adj_opts[adj_stu_label]

                curr_b = balances_df[balances_df["sid"] == adj_sid].iloc[0]
                c_tot = st.number_input("Total Leave Quota", min_value=0, max_value=50, value=int(curr_b["total_leave"]))
                c_used = st.number_input("Used Leave Days", min_value=0, max_value=50, value=int(curr_b["used_leave"]))
                c_rem = c_tot - c_used

                st.write(f"Calculated Remaining: **{c_rem}**")

                if st.form_submit_button("Update Balance Record"):
                    if c_rem < 0:
                        st.error("Used leave cannot exceed total leave quota.")
                    else:
                        ok, _, _ = db.run_dml(queries.UPDATE_LEAVE_BALANCE, {
                            "sid": adj_sid,
                            "total_leave": int(c_tot),
                            "used_leave": int(c_used),
                            "rem_leave": int(c_rem)
                        })
                        if ok:
                            st.success(f"Leave balance updated for {adj_sid}!")
                            st.rerun()

# -----------------------------------------------------------------------------
# TAB 4: APPLICATION HISTORY
# -----------------------------------------------------------------------------
with tab_history:
    st.subheader("All Leave Applications")

    all_leaves_df = db.run_query(queries.GET_ALL_LEAVE_APPLICATIONS)

    if all_leaves_df.empty:
        st.info("No leave application history.")
    else:
        status_filter = st.radio("Filter by Status", ["All", "pending", "approved", "rejected"], horizontal=True)

        filt_df = all_leaves_df.copy()
        if status_filter != "All":
            filt_df = filt_df[filt_df["lstatus"].str.lower() == status_filter.lower()]

        if "ldate" in filt_df.columns:
            filt_df["ldate"] = pd.to_datetime(filt_df["ldate"]).dt.strftime("%Y-%m-%d")

        st.dataframe(
            filt_df.rename(columns={
                "lid": "Application ID",
                "sid": "Student ID",
                "student_name": "Student Name",
                "ldate": "Leave Date",
                "reason": "Reason",
                "lstatus": "Status"
            }),
            use_container_width=True,
            hide_index=True
        )

