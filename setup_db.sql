-- =======================================================
-- Student Attendance & Leave Management System
-- Oracle Schema DDL & PL/SQL Script
-- =======================================================

-- 1. CLEANUP (Optional / Drop existing objects if needed)
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE attendance CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE leave_application CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE leave_balance CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE enrollment CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE subject CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE faculty CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE student CASCADE CONSTRAINTS';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

-- Drop Sequences
BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE seq_fid'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE seq_eid'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE seq_aid'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE seq_lid'; EXCEPTION WHEN OTHERS THEN NULL; END;
/
BEGIN EXECUTE IMMEDIATE 'DROP SEQUENCE seq_bid'; EXCEPTION WHEN OTHERS THEN NULL; END;
/

-- 2. CREATE SEQUENCES
CREATE SEQUENCE seq_fid START WITH 101 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE seq_eid START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE seq_aid START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE seq_lid START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE seq_bid START WITH 1 INCREMENT BY 1 NOCACHE;

-- 3. CREATE TABLES
-- Faculty Table
CREATE TABLE faculty (
    fid NUMBER PRIMARY KEY,
    fname VARCHAR2(50) NOT NULL,
    email VARCHAR2(100) UNIQUE,
    dept VARCHAR2(30) NOT NULL
);

-- Student Table
CREATE TABLE student (
    sid VARCHAR2(10) PRIMARY KEY,
    sname VARCHAR2(50) NOT NULL,
    email VARCHAR2(100) UNIQUE,
    phone VARCHAR2(15),
    dept VARCHAR2(30) NOT NULL,
    sem NUMBER(2) CHECK (sem BETWEEN 1 AND 8)
);

-- Subject Table
CREATE TABLE subject (
    subid VARCHAR2(10) PRIMARY KEY,
    subname VARCHAR2(100) NOT NULL,
    credits NUMBER(2) CHECK (credits > 0),
    sem NUMBER(2) CHECK (sem BETWEEN 1 AND 8),
    fid NUMBER,
    CONSTRAINT fk_sub_fac FOREIGN KEY (fid) REFERENCES faculty(fid)
);

-- Enrollment Table
CREATE TABLE enrollment (
    eid NUMBER PRIMARY KEY,
    sid VARCHAR2(10) NOT NULL,
    subid VARCHAR2(10) NOT NULL,
    edate DATE DEFAULT SYSDATE,
    CONSTRAINT fk_enr_stu FOREIGN KEY (sid) REFERENCES student(sid),
    CONSTRAINT fk_enr_sub FOREIGN KEY (subid) REFERENCES subject(subid),
    CONSTRAINT uq_enr UNIQUE (sid, subid)
);

-- Attendance Table
CREATE TABLE attendance (
    aid NUMBER PRIMARY KEY,
    sid VARCHAR2(10) NOT NULL,
    subid VARCHAR2(10) NOT NULL,
    adate DATE NOT NULL,
    status VARCHAR2(10) NOT NULL,
    CONSTRAINT fk_att_stu FOREIGN KEY (sid) REFERENCES student(sid),
    CONSTRAINT fk_att_sub FOREIGN KEY (subid) REFERENCES subject(subid),
    CONSTRAINT chk_att CHECK (status IN ('present', 'absent')),
    CONSTRAINT uq_att UNIQUE (sid, subid, adate)
);

-- Leave Application Table
CREATE TABLE leave_application (
    lid NUMBER PRIMARY KEY,
    sid VARCHAR2(10) NOT NULL,
    ldate DATE NOT NULL,
    reason VARCHAR2(200),
    lstatus VARCHAR2(20) DEFAULT 'pending',
    CONSTRAINT fk_leave_stu FOREIGN KEY (sid) REFERENCES student(sid),
    CONSTRAINT chk_leave_status CHECK (lstatus IN ('pending', 'approved', 'rejected'))
);

-- Leave Balance Table
CREATE TABLE leave_balance (
    bid NUMBER PRIMARY KEY,
    sid VARCHAR2(10) UNIQUE NOT NULL,
    total_leave NUMBER(3) DEFAULT 15,
    used_leave NUMBER(3) DEFAULT 0,
    rem_leave NUMBER(3),
    CONSTRAINT fk_bal_stu FOREIGN KEY (sid) REFERENCES student(sid),
    CONSTRAINT chk_leave_bal CHECK (
        total_leave >= 0
        AND used_leave >= 0
        AND rem_leave >= 0
    )
);

-- 4. VIEW: low_view (Attendance < 75%)
CREATE OR REPLACE VIEW low_view AS
SELECT 
    s.sid,
    s.sname,
    a.subid,
    ROUND(AVG(CASE WHEN LOWER(a.status) = 'present' THEN 100 ELSE 0 END), 2) AS attperc
FROM student s
JOIN attendance a ON s.sid = a.sid
GROUP BY s.sid, s.sname, a.subid
HAVING AVG(CASE WHEN LOWER(a.status) = 'present' THEN 100 ELSE 0 END) < 75;
/

-- 5. FUNCTION: attfunction (Attendance percentage of a student in a subject)
CREATE OR REPLACE FUNCTION attfunction (
    p_sid   IN VARCHAR2,
    p_subid IN VARCHAR2
) RETURN NUMBER IS
    v_pct NUMBER := 0;
BEGIN
    SELECT ROUND(NVL(AVG(CASE WHEN LOWER(status) = 'present' THEN 100 ELSE 0 END), 0), 2)
    INTO v_pct
    FROM attendance
    WHERE UPPER(sid) = UPPER(p_sid) 
      AND UPPER(subid) = UPPER(p_subid);

    RETURN v_pct;
EXCEPTION
    WHEN OTHERS THEN
        RETURN 0;
END;
/

-- 6. TRIGGER: trg_update_leave_balance
CREATE OR REPLACE TRIGGER trg_update_leave_balance
AFTER UPDATE OF lstatus ON leave_application
FOR EACH ROW
WHEN (old.lstatus = 'pending' AND new.lstatus = 'approved')
BEGIN
    UPDATE leave_balance
    SET used_leave = used_leave + 1,
        rem_leave  = rem_leave - 1
    WHERE sid = :new.sid;
END;
/

-- 7. PROCEDURE: proc_leaveapprov
CREATE OR REPLACE PROCEDURE proc_leaveapprov (
    p_lid IN NUMBER
) IS
    v_sid VARCHAR2(10);
    v_rem NUMBER;
BEGIN
    SELECT la.sid, lb.rem_leave
    INTO v_sid, v_rem
    FROM leave_application la
    JOIN leave_balance lb ON la.sid = lb.sid
    WHERE la.lid = p_lid;

    IF v_rem < 1 THEN
        RAISE_APPLICATION_ERROR(-20001, 'Insufficient leave balance.');
    END IF;

    UPDATE leave_application 
    SET lstatus = 'approved' 
    WHERE lid = p_lid;
    
    COMMIT;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20002, 'Leave ID or Student Balance record not found.');
END;
/

-- 8. SEED DATA FOR QUICK TESTING
INSERT INTO faculty (fid, fname, email, dept) VALUES (101, 'Dr. Alan Turing', 'alan.turing@univ.edu', 'Computer Science');
INSERT INTO faculty (fid, fname, email, dept) VALUES (102, 'Dr. Grace Hopper', 'grace.hopper@univ.edu', 'Computer Science');
INSERT INTO faculty (fid, fname, email, dept) VALUES (103, 'Dr. Claude Shannon', 'claude.shannon@univ.edu', 'Electronics');
INSERT INTO faculty (fid, fname, email, dept) VALUES (106, 'Dr. Ada Lovelace', 'ada.lovelace@univ.edu', 'Mathematics');

INSERT INTO student (sid, sname, email, phone, dept, sem) VALUES ('S001', 'Alice Smith', 'alice@univ.edu', '9876543210', 'Computer Science', 5);
INSERT INTO student (sid, sname, email, phone, dept, sem) VALUES ('S002', 'Bob Jones', 'bob@univ.edu', '9876543211', 'Computer Science', 5);
INSERT INTO student (sid, sname, email, phone, dept, sem) VALUES ('S003', 'Charlie Brown', 'charlie@univ.edu', '9876543212', 'Electronics', 3);
INSERT INTO student (sid, sname, email, phone, dept, sem) VALUES ('S004', 'Diana Prince', 'diana@univ.edu', '9876543213', 'Computer Science', 5);

INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (1, 'S001', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (2, 'S002', 15, 2, 13);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (3, 'S003', 15, 1, 14);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (4, 'S004', 15, 0, 15);

INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('CS501', 'Database Management Systems', 4, 5, 101);
INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('CS502', 'Operating Systems', 4, 5, 102);
INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('EC301', 'Digital Signal Processing', 3, 3, 103);

INSERT INTO enrollment (eid, sid, subid, edate) VALUES (1, 'S001', 'CS501', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (2, 'S001', 'CS502', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (3, 'S002', 'CS501', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (4, 'S002', 'CS502', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (5, 'S003', 'EC301', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (6, 'S004', 'CS501', SYSDATE - 30);

-- Attendance Seed Data (S001 high attendance, S002 low attendance < 75%)
-- S001 CS501 (4 present out of 4 = 100%)
INSERT INTO attendance (aid, sid, subid, adate, status) VALUES (1, 'S001', 'CS501', TRUNC(SYSDATE - 4), 'present');
INSERT INTO attendance (aid, sid, subid, adate, status) VALUES (2, 'S001', 'CS501', TRUNC(SYSDATE - 3), 'present');
INSERT INTO attendance (aid, sid, subid, adate, status) VALUES (3, 'S001', 'CS501', TRUNC(SYSDATE - 2), 'present');
INSERT INTO attendance (aid, sid, subid, adate, status) VALUES (4, 'S001', 'CS501', TRUNC(SYSDATE - 1), 'present');

-- S002 CS501 (1 present out of 4 = 25% -> Low Attendance!)
INSERT INTO attendance (aid, sid, subid, adate, status) VALUES (5, 'S002', 'CS501', TRUNC(SYSDATE - 4), 'absent');
INSERT INTO attendance (aid, sid, subid, adate, status) VALUES (6, 'S002', 'CS501', TRUNC(SYSDATE - 3), 'absent');
INSERT INTO attendance (aid, sid, subid, adate, status) VALUES (7, 'S002', 'CS501', TRUNC(SYSDATE - 2), 'absent');
INSERT INTO attendance (aid, sid, subid, adate, status) VALUES (8, 'S002', 'CS501', TRUNC(SYSDATE - 1), 'present');

-- S004 CS501 (2 present, 2 absent = 50% -> Low Attendance!)
INSERT INTO attendance (aid, sid, subid, adate, status) VALUES (9, 'S004', 'CS501', TRUNC(SYSDATE - 4), 'present');
INSERT INTO attendance (aid, sid, subid, adate, status) VALUES (10, 'S004', 'CS501', TRUNC(SYSDATE - 3), 'absent');
INSERT INTO attendance (aid, sid, subid, adate, status) VALUES (11, 'S004', 'CS501', TRUNC(SYSDATE - 2), 'absent');
INSERT INTO attendance (aid, sid, subid, adate, status) VALUES (12, 'S004', 'CS501', TRUNC(SYSDATE - 1), 'present');

-- Leave Application Seed Data
INSERT INTO leave_application (lid, sid, ldate, reason, lstatus) VALUES (1, 'S001', TRUNC(SYSDATE + 2), 'Medical checkup', 'pending');
INSERT INTO leave_application (lid, sid, ldate, reason, lstatus) VALUES (2, 'S002', TRUNC(SYSDATE - 10), 'Family event', 'approved');
INSERT INTO leave_application (lid, sid, ldate, reason, lstatus) VALUES (3, 'S003', TRUNC(SYSDATE + 5), 'Conference attendance', 'pending');

COMMIT;

