"""
SQL queries and commands repository for Student Attendance & Leave Management System.
Corresponds to schema, views, procedures, functions, and queries defined in projecttables.txt.
"""

# ==============================================================================
# 1. FACULTY QUERIES
# ==============================================================================
GET_ALL_FACULTY = """
    SELECT fid, fname, email, dept
    FROM faculty
    ORDER BY fid ASC
"""

GET_FACULTY_ORDERED_BY_NAME = """
    SELECT fid, fname, email, dept
    FROM faculty
    ORDER BY fname ASC
"""

GET_FACULTY_FILTER_MIN_ID = """
    SELECT fname, fid, email, dept
    FROM faculty
    WHERE fid > :min_id
    ORDER BY fid ASC
"""

GET_FACULTY_BY_ID = """
    SELECT fid, fname, email, dept
    FROM faculty
    WHERE fid = :fid
"""

INSERT_FACULTY = """
    INSERT INTO faculty (fid, fname, email, dept)
    VALUES (:fid, :fname, :email, :dept)
"""

UPDATE_FACULTY = """
    UPDATE faculty
    SET fname = :fname,
        email = :email,
        dept = :dept
    WHERE fid = :fid
"""

DELETE_FACULTY = """
    DELETE FROM faculty
    WHERE fid = :fid
"""

GET_NEXT_FACULTY_ID = """
    SELECT NVL(MAX(fid), 100) + 1 AS next_id FROM faculty
"""

# ==============================================================================
# 2. STUDENT QUERIES
# ==============================================================================
GET_ALL_STUDENTS = """
    SELECT sid, sname, email, phone, dept, sem
    FROM student
    ORDER BY sid ASC
"""

GET_STUDENTS_ORDERED_BY_NAME = """
    SELECT sid, sname, email, phone, dept, sem
    FROM student
    ORDER BY sname ASC
"""

SEARCH_STUDENTS_BY_NAME = """
    SELECT sid, sname, email, phone, dept, sem
    FROM student
    WHERE LOWER(sname) LIKE LOWER(:term)
    ORDER BY sname ASC
"""

GET_STUDENT_BY_ID = """
    SELECT sid, sname, email, phone, dept, sem
    FROM student
    WHERE sid = :sid
"""

INSERT_STUDENT = """
    INSERT INTO student (sid, sname, email, phone, dept, sem)
    VALUES (:sid, :sname, :email, :phone, :dept, :sem)
"""

UPDATE_STUDENT = """
    UPDATE student
    SET sname = :sname,
        email = :email,
        phone = :phone,
        dept = :dept,
        sem = :sem
    WHERE sid = :sid
"""

DELETE_STUDENT = """
    DELETE FROM student
    WHERE sid = :sid
"""

# ==============================================================================
# 3. SUBJECT QUERIES
# ==============================================================================
GET_ALL_SUBJECTS = """
    SELECT s.subid, s.subname, s.credits, s.sem, s.fid, f.fname AS faculty_name
    FROM subject s
    LEFT JOIN faculty f ON s.fid = f.fid
    ORDER BY s.subid ASC
"""

GET_SUBJECT_BY_ID = """
    SELECT subid, subname, credits, sem, fid
    FROM subject
    WHERE subid = :subid
"""

INSERT_SUBJECT = """
    INSERT INTO subject (subid, subname, credits, sem, fid)
    VALUES (:subid, :subname, :credits, :sem, :fid)
"""

UPDATE_SUBJECT = """
    UPDATE subject
    SET subname = :subname,
        credits = :credits,
        sem = :sem,
        fid = :fid
    WHERE subid = :subid
"""

DELETE_SUBJECT = """
    DELETE FROM subject
    WHERE subid = :subid
"""

# ==============================================================================
# 4. ENROLLMENT QUERIES
# ==============================================================================
GET_ALL_ENROLLMENTS = """
    SELECT e.eid, e.sid, st.sname AS student_name, e.subid, sub.subname AS subject_name, e.edate
    FROM enrollment e
    JOIN student st ON e.sid = st.sid
    JOIN subject sub ON e.subid = sub.subid
    ORDER BY e.eid DESC
"""

GET_STUDENTS_ENROLLED_IN_SUBJECT = """
    SELECT e.eid, e.sid, st.sname, st.email, st.dept, st.sem
    FROM enrollment e
    JOIN student st ON e.sid = st.sid
    WHERE e.subid = :subid
    ORDER BY st.sname ASC
"""

CHECK_ENROLLMENT_EXISTS = """
    SELECT COUNT(*) AS cnt
    FROM enrollment
    WHERE sid = :sid AND subid = :subid
"""

INSERT_ENROLLMENT = """
    INSERT INTO enrollment (eid, sid, subid, edate)
    VALUES (:eid, :sid, :subid, :edate)
"""

DELETE_ENROLLMENT = """
    DELETE FROM enrollment
    WHERE eid = :eid
"""

GET_NEXT_ENROLLMENT_ID = """
    SELECT NVL(MAX(eid), 0) + 1 AS next_id FROM enrollment
"""

# ==============================================================================
# 5. ATTENDANCE QUERIES
# ==============================================================================
GET_ALL_ATTENDANCE = """
    SELECT a.aid, a.sid, s.sname AS student_name, a.subid, sub.subname AS subject_name, a.adate, a.status
    FROM attendance a
    JOIN student s ON a.sid = s.sid
    JOIN subject sub ON a.subid = sub.subid
    ORDER BY a.adate DESC, a.aid DESC
"""

GET_ATTENDANCE_FILTERED = """
    SELECT a.aid, a.sid, s.sname AS student_name, a.subid, sub.subname AS subject_name, a.adate, a.status
    FROM attendance a
    JOIN student s ON a.sid = s.sid
    JOIN subject sub ON a.subid = sub.subid
    WHERE (:subid IS NULL OR a.subid = :subid)
      AND (:adate IS NULL OR TRUNC(a.adate) = TRUNC(:adate))
    ORDER BY a.adate DESC, s.sname ASC
"""

CHECK_ATTENDANCE_EXISTS = """
    SELECT COUNT(*) AS cnt
    FROM attendance
    WHERE sid = :sid AND subid = :subid AND TRUNC(adate) = TRUNC(:adate)
"""

INSERT_ATTENDANCE = """
    INSERT INTO attendance (aid, sid, subid, adate, status)
    VALUES (:aid, :sid, :subid, :adate, :status)
"""

UPDATE_ATTENDANCE = """
    UPDATE attendance
    SET status = :status
    WHERE aid = :aid
"""

DELETE_ATTENDANCE = """
    DELETE FROM attendance
    WHERE aid = :aid
"""

GET_NEXT_ATTENDANCE_ID = """
    SELECT NVL(MAX(aid), 0) + 1 AS next_id FROM attendance
"""

# Function call: attfunction(p_sid, p_subid)
CALL_ATTFUNCTION = """
    SELECT attfunction(:sid, :subid) AS attendance_pct FROM dual
"""

# Low Attendance View query (< 75%)
GET_LOW_ATTENDANCE_VIEW = """
    SELECT sid, sname, subid, attperc
    FROM low_view
    ORDER BY attperc ASC
"""

# Low Attendance direct JOIN query (< 75%)
GET_LOW_ATTENDANCE_JOIN = """
    SELECT s.sid,
           s.sname,
           a.subid,
           ROUND(
               SUM(CASE WHEN LOWER(a.status) = 'present' THEN 1 ELSE 0 END)
               * 100 / COUNT(*),
               2
           ) AS attendance_percentage
    FROM student s
    JOIN attendance a ON s.sid = a.sid
    GROUP BY s.sid, s.sname, a.subid
    HAVING SUM(CASE WHEN LOWER(a.status) = 'present' THEN 1 ELSE 0 END)
           * 100 / COUNT(*) < 75
    ORDER BY attendance_percentage ASC
"""

# ==============================================================================
# 6. LEAVE QUERIES
# ==============================================================================
GET_PENDING_LEAVE_APPLICATIONS = """
    SELECT la.lid, la.sid, s.sname AS student_name, s.dept, la.ldate, la.reason, la.lstatus, lb.rem_leave
    FROM leave_application la
    JOIN student s ON la.sid = s.sid
    LEFT JOIN leave_balance lb ON la.sid = lb.sid
    WHERE LOWER(la.lstatus) = 'pending'
    ORDER BY la.ldate ASC
"""

GET_ALL_LEAVE_APPLICATIONS = """
    SELECT la.lid, la.sid, s.sname AS student_name, la.ldate, la.reason, la.lstatus
    FROM leave_application la
    JOIN student s ON la.sid = s.sid
    ORDER BY la.lid DESC
"""

INSERT_LEAVE_APPLICATION = """
    INSERT INTO leave_application (lid, sid, ldate, reason, lstatus)
    VALUES (:lid, :sid, :ldate, :reason, 'pending')
"""

REJECT_LEAVE_APPLICATION = """
    UPDATE leave_application
    SET lstatus = 'rejected'
    WHERE lid = :lid
"""

GET_NEXT_LEAVE_APP_ID = """
    SELECT NVL(MAX(lid), 0) + 1 AS next_id FROM leave_application
"""

# Leave Balance Queries
GET_ALL_LEAVE_BALANCES = """
    SELECT lb.bid, lb.sid, s.sname AS student_name, s.dept, lb.total_leave, lb.used_leave, lb.rem_leave
    FROM leave_balance lb
    JOIN student s ON lb.sid = s.sid
    ORDER BY s.sname ASC
"""

GET_LEAVE_BALANCE_BY_STUDENT = """
    SELECT bid, sid, total_leave, used_leave, rem_leave
    FROM leave_balance
    WHERE sid = :sid
"""

INSERT_LEAVE_BALANCE = """
    INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave)
    VALUES (:bid, :sid, :total_leave, :used_leave, :rem_leave)
"""

UPDATE_LEAVE_BALANCE = """
    UPDATE leave_balance
    SET total_leave = :total_leave,
        used_leave = :used_leave,
        rem_leave = :rem_leave
    WHERE sid = :sid
"""

GET_NEXT_LEAVE_BAL_ID = """
    SELECT NVL(MAX(bid), 0) + 1 AS next_id FROM leave_balance
"""

# ==============================================================================
# 7. ANALYTICS QUERIES
# ==============================================================================
# Cursor-equivalent query: identifies students whose overall attendance is below 75%
GET_CURSOR_LOW_ATTENDANCE = """
    SELECT a.sid,
           s.sname AS student_name,
           ROUND(SUM(CASE WHEN LOWER(a.status) = 'present' THEN 1 ELSE 0 END)
           * 100 / COUNT(*), 2) AS att_per,
           SUM(CASE WHEN LOWER(a.status) = 'present' THEN 1 ELSE 0 END) AS attended_classes,
           COUNT(*) AS total_classes
    FROM attendance a
    JOIN student s ON a.sid = s.sid
    GROUP BY a.sid, s.sname
    HAVING SUM(CASE WHEN LOWER(a.status) = 'present' THEN 1 ELSE 0 END)
           * 100 / COUNT(*) < 75
    ORDER BY att_per ASC
"""

# Subject-wise attendance trend analysis
GET_SUBJECT_WISE_ATTENDANCE_TREND = """
    SELECT a.subid,
           sub.subname AS subject_name,
           ROUND(SUM(CASE WHEN LOWER(a.status) = 'present' THEN 1 ELSE 0 END)
           * 100 / COUNT(*), 2) AS attendance_percentage,
           COUNT(*) AS total_records
    FROM attendance a
    LEFT JOIN subject sub ON a.subid = sub.subid
    GROUP BY a.subid, sub.subname
    ORDER BY attendance_percentage DESC
"""

# System summary counts for dashboard
GET_DASHBOARD_METRICS = {
    "total_students": "SELECT COUNT(*) AS cnt FROM student",
    "total_faculty": "SELECT COUNT(*) AS cnt FROM faculty",
    "total_subjects": "SELECT COUNT(*) AS cnt FROM subject",
    "total_attendance": "SELECT COUNT(*) AS cnt FROM attendance",
    "pending_leaves": "SELECT COUNT(*) AS cnt FROM leave_application WHERE LOWER(lstatus) = 'pending'",
    "low_attendance_students": """
        SELECT COUNT(DISTINCT sid) AS cnt
        FROM (
            SELECT sid
            FROM attendance
            GROUP BY sid
            HAVING SUM(CASE WHEN LOWER(status) = 'present' THEN 1 ELSE 0 END) * 100 / COUNT(*) < 75
        )
    """
}

