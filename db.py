"""
Database helper module for Student Attendance & Leave Management System.

Talks to Oracle Database 10g through the SQL*Plus command-line client
(subprocess bridge), which avoids the 32-bit client / 64-bit Python mismatch
and the fact that python-oracledb thin mode cannot connect to 10g servers.

Query results are produced with SET MARKUP HTML ON and parsed with a
zero-dependency HTML parser into pandas DataFrames.
"""

import os
import re
import shutil
import subprocess
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st


# --------------------------------------------------------------------------
# HTML parsing of SQL*Plus output
# --------------------------------------------------------------------------

class SimpleHTMLTableParser(HTMLParser):
    """Extracts <table> content from SQL*Plus HTML output into lists of rows."""

    def __init__(self):
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self.current_table: List[List[str]] = []
        self.current_row: List[str] = []
        self.current_cell: List[str] = []
        self.in_cell = False

    def handle_starttag(self, tag: str, attrs: Any):
        if tag == "table":
            self.current_table = []
        elif tag == "tr":
            self.current_row = []
        elif tag in ("td", "th"):
            self.in_cell = True
            self.current_cell = []

    def handle_data(self, data: str):
        if self.in_cell:
            self.current_cell.append(data)

    def handle_entityref(self, name: str):
        if self.in_cell and name == "nbsp":
            self.current_cell.append(" ")

    def handle_charref(self, name: str):
        if self.in_cell and name in ("160", "xa0", "XA0"):
            self.current_cell.append(" ")

    def handle_endtag(self, tag: str):
        if tag in ("td", "th"):
            self.in_cell = False
            self.current_row.append("".join(self.current_cell).replace("\xa0", " ").strip())
        elif tag == "tr":
            if self.current_row:
                self.current_table.append(self.current_row)
        elif tag == "table":
            if self.current_table:
                self.tables.append(self.current_table)


# --------------------------------------------------------------------------
# Credentials and SQL*Plus location
# --------------------------------------------------------------------------

def get_db_credentials() -> Dict[str, str]:
    """
    Resolve Oracle settings from (1) session state, (2) st.secrets,
    (3) environment variables / defaults - in that order.
    """
    if st.session_state.get("oracle_credentials"):
        return st.session_state["oracle_credentials"]

    creds = {
        "user": os.getenv("ORACLE_USER", "system"),
        "password": os.getenv("ORACLE_PASSWORD", "oracle123"),
        "dsn": os.getenv("ORACLE_DSN", "ORCL"),
        "sqlplus_path": os.getenv(
            "SQLPLUS_PATH",
            r"C:\oracle\product\10.2.0\db_1\bin\sqlplus.exe",
        ),
    }

    try:
        if "oracle" in st.secrets:
            sec = st.secrets["oracle"]
            creds["user"] = sec.get("user", creds["user"])
            creds["password"] = sec.get("password", creds["password"])
            creds["dsn"] = sec.get("dsn", creds["dsn"])
            if "sqlplus_path" in sec:
                creds["sqlplus_path"] = sec["sqlplus_path"]
    except Exception:
        # st.secrets raises if no secrets.toml exists - fall through to defaults.
        pass

    return creds


def get_sqlplus_executable() -> str:
    """Locate sqlplus.exe: configured path, then common install dirs, then PATH."""
    configured_path = get_db_credentials().get("sqlplus_path")
    if configured_path and os.path.isfile(configured_path):
        return configured_path

    candidates = [
        r"C:\oracle\product\10.2.0\db_1\bin\sqlplus.exe",
        r"C:\oraclexe\app\oracle\product\10.2.0\server\bin\sqlplus.exe",
        r"C:\app\oracle\product\11.2.0\dbhome_1\bin\sqlplus.exe",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p

    return shutil.which("sqlplus") or "sqlplus"


# --------------------------------------------------------------------------
# SQL*Plus execution
# --------------------------------------------------------------------------

def substitute_params(sql: str, params: Optional[Dict[str, Any]]) -> str:
    """
    Inline named parameters (:name) into SQL, since SQL*Plus has no bind API here.
    Longest keys first so :student_id is not clobbered by :student.
    """
    if not params:
        return sql

    for key in sorted(params.keys(), key=len, reverse=True):
        sql = re.sub(r":" + re.escape(key) + r"\b", _format_literal(params[key]), sql)

    return sql


def _format_literal(val: Any) -> str:
    """Render a Python value as an Oracle SQL literal."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, datetime):
        return f"TO_DATE('{val.strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"
    if isinstance(val, date):
        return f"TO_DATE('{val.strftime('%Y-%m-%d')}', 'YYYY-MM-DD')"
    return "'" + str(val).replace("'", "''") + "'"


def parse_student_semester(value: Any) -> Optional[int]:
    """Parse semester values stored as either numbers, digit strings, or labels like 'S5'."""
    match = re.search(r"\d+", str(value))
    if not match:
        return None

    semester = int(match.group())
    return semester if 1 <= semester <= 8 else None


def run_sqlplus_command(input_sql: str, timeout: int = 30) -> Tuple[int, str, str]:
    """Pipe a script into sqlplus -S -L and return (returncode, stdout, stderr)."""
    creds = get_db_credentials()
    connect_str = f"{creds.get('user', 'system')}/{creds.get('password', '')}@{creds.get('dsn', 'ORCL')}"
    cmd = [get_sqlplus_executable(), "-S", "-L", connect_str]

    try:
        proc = subprocess.run(
            cmd,
            input=input_sql,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return -1, "", "sqlplus.exe not found. Set sqlplus_path in the sidebar or secrets.toml."
    except subprocess.TimeoutExpired:
        return -1, "", f"SQL*Plus timed out after {timeout}s."
    except Exception as e:
        return -1, "", str(e)


def test_connection() -> Tuple[bool, str]:
    """Return (is_connected, banner_or_error)."""
    sql = "SET PAGESIZE 0\nSET FEEDBACK OFF\nSELECT banner FROM v$version WHERE ROWNUM = 1;\nEXIT;\n"
    rc, stdout, stderr = run_sqlplus_command(sql, timeout=15)

    if rc == 0 and "ORA-" not in stdout and "Oracle" in stdout:
        lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
        return True, lines[0] if lines else "Connected to Oracle Database"

    err = stdout.strip() if "ORA-" in stdout else (stderr.strip() or stdout.strip())
    return False, err or "Could not connect to Oracle"


# --------------------------------------------------------------------------
# Queries and DML
# --------------------------------------------------------------------------

def run_query(sql: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Run a SELECT through SQL*Plus and return the rows as a DataFrame."""
    clean_sql = substitute_params(sql.strip(), params).rstrip("; \t\n")

    script = f"""SET MARKUP HTML ON ENTMAP OFF SPOOL OFF PREFORMAT OFF
SET PAGESIZE 50000
SET FEEDBACK OFF
SET ECHO OFF
SET LINESIZE 32767
{clean_sql};
EXIT;
"""
    rc, stdout, stderr = run_sqlplus_command(script)

    if "ORA-" in stdout:
        st.error(f"Oracle Query Error:\n{stdout.strip()}")
        return pd.DataFrame()
    if rc != 0:
        st.error(f"Execution Error:\n{stderr.strip() or stdout.strip()}")
        return pd.DataFrame()

    parser = SimpleHTMLTableParser()
    parser.feed(stdout)

    if not parser.tables or len(parser.tables[0]) < 1:
        return pd.DataFrame()

    rows = parser.tables[0]
    headers = [h.lower().strip() for h in rows[0]]
    df = pd.DataFrame(rows[1:], columns=headers)

    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().all() and len(df) > 0:
            df[col] = converted

    return df


def run_dml(sql: str, params: Optional[Dict[str, Any]] = None) -> Tuple[bool, int, Optional[str]]:
    """Run INSERT/UPDATE/DELETE and COMMIT. Returns (success, rows_affected, error)."""
    clean_sql = substitute_params(sql.strip(), params).rstrip("; \t\n")

    script = f"""SET FEEDBACK ON
SET ECHO OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE
{clean_sql};
COMMIT;
EXIT;
"""
    rc, stdout, stderr = run_sqlplus_command(script)

    if "ORA-" in stdout:
        err = stdout.strip()
        st.error(f"Oracle DML Error:\n{err}")
        return False, 0, err
    if rc != 0:
        err = stderr.strip() or stdout.strip()
        st.error(f"Execution Error:\n{err}")
        return False, 0, err

    match = re.search(r"(\d+)\s+rows?\s+(?:created|updated|deleted|merged)", stdout, re.IGNORECASE)
    return True, int(match.group(1)) if match else 1, None


# --------------------------------------------------------------------------
# Stored procedures and functions
# --------------------------------------------------------------------------

def call_proc(proc_name: str, params: list) -> Tuple[bool, Optional[str]]:
    """Call a stored procedure (e.g. proc_leaveapprov) and COMMIT."""
    args_str = ", ".join(_format_literal(p) for p in params)

    script = f"""SET SERVEROUTPUT ON
SET FEEDBACK OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE
BEGIN
    {proc_name}({args_str});
END;
/
COMMIT;
EXIT;
"""
    rc, stdout, stderr = run_sqlplus_command(script)

    if "ORA-" in stdout:
        err = stdout.strip()
        st.error(f"Procedure Execution Error ({proc_name}):\n{err}")
        return False, err
    if rc != 0:
        err = stderr.strip() or stdout.strip()
        st.error(f"Execution Error ({proc_name}):\n{err}")
        return False, err

    return True, None


def call_func(func_name: str, params: list) -> Tuple[bool, Any, Optional[str]]:
    """Call a stored function (e.g. attfunction) via SELECT ... FROM dual."""
    args_str = ", ".join(_format_literal(p) for p in params)
    df = run_query(f"SELECT {func_name}({args_str}) AS result_val FROM dual")

    if not df.empty and "result_val" in df.columns:
        return True, df.iloc[0]["result_val"], None

    return False, None, f"Function {func_name} did not return a value."


def execute_sql_script(sql_file_path: str) -> Tuple[bool, str]:
    """Run a full .sql script (e.g. setup_db.sql) with SQL*Plus @script."""
    if not os.path.exists(sql_file_path):
        return False, f"File not found: {sql_file_path}"

    abs_script = os.path.abspath(sql_file_path)
    rc, stdout, stderr = run_sqlplus_command(f"@\"{abs_script}\"\nEXIT;\n", timeout=120)

    if rc == 0 and "ORA-" not in stdout:
        return True, "Database setup script executed successfully."

    return False, (stdout.strip() or stderr.strip() or "Script execution failed.")


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------

def render_sidebar():
    """Sidebar with branding and Oracle connection settings."""
    st.sidebar.title("🎓 Attendance & Leave")
    st.sidebar.caption("Oracle 10g Streamlit Portal")
    st.sidebar.markdown("---")

    with st.sidebar.expander("🔌 Database Connection", expanded=False):
        current = get_db_credentials()
        st.caption("Oracle Database Settings:")

        new_user = st.text_input("User", value=current.get("user", "system"), key="sb_user")
        new_pass = st.text_input("Password", value=current.get("password", ""), type="password", key="sb_pass")
        new_dsn = st.text_input("DSN / TNS Alias", value=current.get("dsn", "ORCL"), key="sb_dsn")
        new_path = st.text_input("Path to sqlplus.exe", value=current.get("sqlplus_path", ""), key="sb_sqlplus")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save & Test", use_container_width=True, key="btn_save_test_conn"):
                st.session_state["oracle_credentials"] = {
                    "user": new_user.strip(),
                    "password": new_pass.strip(),
                    "dsn": new_dsn.strip(),
                    "sqlplus_path": new_path.strip(),
                }
                ok, msg = test_connection()
                if ok:
                    st.success("Connected!")
                    st.caption(msg[:60])
                else:
                    st.error(f"Failed:\n{msg[:200]}")

        with col2:
            if st.button("Check Status", use_container_width=True, key="btn_check_conn_status"):
                ok, _ = test_connection()
                st.success("Online") if ok else st.error("Offline")

        st.markdown("---")
        st.caption("Initialize or re-seed database schema:")
        if st.button("Run setup_db.sql", use_container_width=True, key="btn_run_setup_sql"):
            script_path = Path(__file__).parent / "setup_db.sql"
            if script_path.exists():
                with st.spinner("Executing schema setup..."):
                    ok, res = execute_sql_script(str(script_path))
                    st.success(res) if ok else st.error(f"Setup failed:\n{res}")
            else:
                st.warning("setup_db.sql not found.")

    is_conn, _ = test_connection()
    creds = get_db_credentials()
    if is_conn:
        st.sidebar.success("● Oracle 10g: Connected")
        st.sidebar.caption(f"User: `{creds.get('user')}` | DSN: `{creds.get('dsn')}`")
    else:
        st.sidebar.warning("○ Oracle 10g: Disconnected")
        st.sidebar.caption("Open 'Database Connection' above to configure credentials.")