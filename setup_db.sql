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
    dept VARCHAR2(30) NOT NULL,
    sem NUMBER(2) CHECK (sem BETWEEN 1 AND 8),
    cgpa NUMBER(3,2) CHECK (cgpa BETWEEN 0 AND 10)
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
JOIN attendance a ON TO_CHAR(s.sid) = a.sid
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

INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S001', 'Alice Smith', 'Computer Science', 5, 8.50);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S002', 'Bob Jones', 'Computer Science', 5, 7.20);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S003', 'Charlie Brown', 'Electronics', 3, 8.10);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S004', 'Diana Prince', 'Computer Science', 5, 9.00);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S005', 'Ethan Clark', 'Computer Science', 1, 7.80);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S006', 'Fiona Garcia', 'Electronics', 1, 8.30);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S007', 'George Miller', 'Mathematics', 2, 7.60);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S008', 'Hannah Wilson', 'Computer Science', 2, 9.10);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S009', 'Isaac Moore', 'Electronics', 3, 6.90);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S010', 'Julia Taylor', 'Computer Science', 3, 8.40);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S011', 'Kevin Anderson', 'Mathematics', 4, 7.50);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S012', 'Lily Thomas', 'Electronics', 4, 9.20);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S013', 'Marcus Jackson', 'Computer Science', 5, 8.00);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S014', 'Nora White', 'Electronics', 5, 7.70);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S015', 'Owen Harris', 'Mathematics', 6, 8.60);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S016', 'Priya Martin', 'Computer Science', 6, 9.40);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S017', 'Quinn Thompson', 'Electronics', 7, 7.30);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S018', 'Riya Lee', 'Computer Science', 7, 8.70);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S019', 'Samuel Walker', 'Mathematics', 8, 8.20);
INSERT INTO student (sid, sname, dept, sem, cgpa) VALUES ('S020', 'Tara Young', 'Computer Science', 8, 9.10);

INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (1, 'S001', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (2, 'S002', 15, 2, 13);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (3, 'S003', 15, 1, 14);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (4, 'S004', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (5, 'S005', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (6, 'S006', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (7, 'S007', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (8, 'S008', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (9, 'S009', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (10, 'S010', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (11, 'S011', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (12, 'S012', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (13, 'S013', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (14, 'S014', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (15, 'S015', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (16, 'S016', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (17, 'S017', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (18, 'S018', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (19, 'S019', 15, 0, 15);
INSERT INTO leave_balance (bid, sid, total_leave, used_leave, rem_leave) VALUES (20, 'S020', 15, 0, 15);

INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('CS501', 'Database Management Systems', 4, 5, 101);
INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('CS502', 'Operating Systems', 4, 5, 102);
INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('EC301', 'Digital Signal Processing', 3, 3, 103);
INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('DM01', 'Foundations of Computing', 3, 1, 101);
INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('DM02', 'Programming Fundamentals', 3, 2, 101);
INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('DM03', 'Digital Systems', 3, 3, 103);
INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('DM04', 'Data Structures', 4, 4, 101);
INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('DM05', 'Database Systems Lab', 3, 5, 101);
INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('DM06', 'Computer Networks', 3, 6, 101);
INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('DM07', 'Embedded Systems', 3, 7, 103);
INSERT INTO subject (subid, subname, credits, sem, fid) VALUES ('DM08', 'Project Seminar', 2, 8, 106);

INSERT INTO enrollment (eid, sid, subid, edate) VALUES (1, 'S001', 'CS501', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (2, 'S001', 'CS502', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (3, 'S002', 'CS501', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (4, 'S002', 'CS502', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (5, 'S003', 'EC301', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (6, 'S004', 'CS501', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (7, 'S005', 'DM01', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (8, 'S006', 'DM01', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (9, 'S007', 'DM02', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (10, 'S008', 'DM02', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (11, 'S009', 'DM03', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (12, 'S010', 'DM03', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (13, 'S011', 'DM04', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (14, 'S012', 'DM04', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (15, 'S013', 'DM05', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (16, 'S014', 'DM05', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (17, 'S015', 'DM06', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (18, 'S016', 'DM06', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (19, 'S017', 'DM07', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (20, 'S018', 'DM07', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (21, 'S019', 'DM08', SYSDATE - 30);
INSERT INTO enrollment (eid, sid, subid, edate) VALUES (22, 'S020', 'DM08', SYSDATE - 30);

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

-- Demo student attendance: three sessions each, with varied attendance percentages.
INSERT INTO attendance (aid, sid, subid, adate, status)
SELECT 12 + ROW_NUMBER() OVER (ORDER BY s.sid, session_days.session_no),
       s.sid,
       'DM' || LPAD(s.sem, 2, '0'),
       TO_DATE('2026-11-01', 'YYYY-MM-DD') - session_days.session_no,
       CASE
           WHEN MOD(TO_NUMBER(SUBSTR(s.sid, 2)) + session_days.session_no, 3) = 0 THEN 'absent'
           ELSE 'present'
       END
FROM student s
JOIN (
    SELECT LEVEL AS session_no
    FROM dual
    CONNECT BY LEVEL <= 3
) session_days ON 1 = 1
WHERE s.sid BETWEEN 'S005' AND 'S020';

-- Leave Application Seed Data
INSERT INTO leave_application (lid, sid, ldate, reason, lstatus) VALUES (1, 'S001', TRUNC(SYSDATE + 2), 'Medical checkup', 'pending');
INSERT INTO leave_application (lid, sid, ldate, reason, lstatus) VALUES (2, 'S002', TRUNC(SYSDATE - 10), 'Family event', 'approved');
INSERT INTO leave_application (lid, sid, ldate, reason, lstatus) VALUES (3, 'S003', TRUNC(SYSDATE + 5), 'Conference attendance', 'pending');
INSERT INTO leave_application (lid, sid, ldate, reason, lstatus) VALUES (4, 'S005', TRUNC(SYSDATE + 2), 'Demo student medical leave', 'pending');
INSERT INTO leave_application (lid, sid, ldate, reason, lstatus) VALUES (5, 'S009', TRUNC(SYSDATE + 4), 'Demo student family event', 'pending');
INSERT INTO leave_application (lid, sid, ldate, reason, lstatus) VALUES (6, 'S013', TRUNC(SYSDATE - 3), 'Demo student appointment', 'rejected');

COMMIT;
