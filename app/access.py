from __future__ import annotations
import hmac
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from app.schemas import EmployeeRecord, ActivityRecord

@dataclass(frozen=True)
class AccessSession:
    session_id: str
    employee_id: str
    role: str
    login_event_id: int
    admin_unlocked: bool

def now() -> str: return datetime.now(timezone.utc).isoformat()

class AccessStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS employees (employee_id TEXT PRIMARY KEY, role TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS login_events (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT NOT NULL, ip_address TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, employee_id TEXT NOT NULL, login_event_id INTEGER NOT NULL, admin_unlocked INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS activities (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT NOT NULL, login_event_id INTEGER NOT NULL, action TEXT NOT NULL, contract_name TEXT NOT NULL, created_at TEXT NOT NULL);
            """)
            connection.execute("INSERT OR IGNORE INTO employees VALUES (?, ?, ?)", ("1", "admin", now()))
            connection.execute("INSERT OR IGNORE INTO employees VALUES (?, ?, ?)", ("2", "user", now()))
            connection.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)", ("admin_password", "1"))

    def login(self, employee_id: str, ip_address: str) -> AccessSession | None:
        employee_id = employee_id.strip()
        with self._connect() as connection:
            employee = connection.execute("SELECT employee_id, role FROM employees WHERE employee_id = ?", (employee_id,)).fetchone()
            if employee is None: return None
            login_event_id = connection.execute("INSERT INTO login_events (employee_id, ip_address, created_at) VALUES (?, ?, ?)", (employee_id, ip_address, now())).lastrowid
            session_id = secrets.token_urlsafe(32)
            connection.execute("INSERT INTO sessions VALUES (?, ?, ?, 0, ?)", (session_id, employee_id, login_event_id, now()))
            return AccessSession(session_id, employee_id, employee["role"], login_event_id, False)

    def session(self, session_id: str | None) -> AccessSession | None:
        if not session_id: return None
        with self._connect() as connection:
            row = connection.execute("SELECT sessions.session_id, sessions.employee_id, sessions.login_event_id, sessions.admin_unlocked, employees.role FROM sessions JOIN employees ON employees.employee_id = sessions.employee_id WHERE sessions.session_id = ?", (session_id,)).fetchone()
            return None if row is None else AccessSession(row["session_id"], row["employee_id"], row["role"], row["login_event_id"], bool(row["admin_unlocked"]))

    def logout(self, session_id: str | None) -> None:
        if session_id:
            with self._connect() as connection: connection.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def unlock_admin(self, session: AccessSession, password: str) -> bool:
        if session.role != "admin": return False
        with self._connect() as connection:
            configured = connection.execute("SELECT value FROM settings WHERE key = 'admin_password'").fetchone()["value"]
            if not hmac.compare_digest(configured, password): return False
            connection.execute("UPDATE sessions SET admin_unlocked = 1 WHERE session_id = ?", (session.session_id,))
            return True

    def change_admin_password(self, session: AccessSession, current_password: str, new_password: str) -> bool:
        if session.role != "admin": return False
        with self._connect() as connection:
            configured = connection.execute("SELECT value FROM settings WHERE key = 'admin_password'").fetchone()["value"]
            if not hmac.compare_digest(configured, current_password): return False
            connection.execute("UPDATE settings SET value = ? WHERE key = 'admin_password'", (new_password,))
            return True

    def clear_sessions(self) -> None:
        with self._connect() as connection: connection.execute("DELETE FROM sessions")

    def record_activity(self, session: AccessSession, action: str, contract_name: str) -> None:
        with self._connect() as connection:
            connection.execute("INSERT INTO activities (employee_id, login_event_id, action, contract_name, created_at) VALUES (?, ?, ?, ?, ?)", (session.employee_id, session.login_event_id, action, contract_name, now()))

    def employees(self) -> list[EmployeeRecord]:
        with self._connect() as connection:
            return [EmployeeRecord(employee_id=row["employee_id"], role=row["role"], created_at=row["created_at"]) for row in connection.execute("SELECT * FROM employees ORDER BY employee_id")]

    def add_employee(self, employee_id: str, role: str) -> EmployeeRecord:
        employee_id = employee_id.strip()
        with self._connect() as connection:
            try: connection.execute("INSERT INTO employees VALUES (?, ?, ?)", (employee_id, role, now()))
            except sqlite3.IntegrityError as exc: raise ValueError("工号已存在") from exc
        return next(item for item in self.employees() if item.employee_id == employee_id)

    def update_role(self, employee_id: str, role: str) -> EmployeeRecord:
        with self._connect() as connection:
            if connection.execute("UPDATE employees SET role = ? WHERE employee_id = ?", (role, employee_id)).rowcount == 0: raise KeyError(employee_id)
        return next(item for item in self.employees() if item.employee_id == employee_id)

    def delete_employee(self, employee_id: str) -> None:
        if employee_id == "1": raise ValueError("初始管理员工号不能删除")
        with self._connect() as connection:
            if connection.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,)).rowcount == 0: raise KeyError(employee_id)
            connection.execute("DELETE FROM sessions WHERE employee_id = ?", (employee_id,))

    def activities(self) -> list[ActivityRecord]:
        query = """SELECT activities.employee_id, employees.role, activities.action, activities.contract_name, activities.created_at, login_events.ip_address
            FROM activities JOIN employees ON employees.employee_id = activities.employee_id JOIN login_events ON login_events.id = activities.login_event_id ORDER BY activities.id DESC"""
        with self._connect() as connection:
            return [ActivityRecord(employee_id=row["employee_id"], role=row["role"], action=row["action"], contract_name=row["contract_name"], created_at=row["created_at"], ip_address=row["ip_address"]) for row in connection.execute(query)]
