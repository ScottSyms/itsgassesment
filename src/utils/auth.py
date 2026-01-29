"""Authentication and authorization helpers."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import BadSignature, URLSafeSerializer


AUTH_DB_PATH = os.getenv("AUTH_DB_PATH", "./data/auth.db")
SESSION_TTL_MINUTES = int(os.getenv("SESSION_TTL_MINUTES", "120"))
SESSION_IDLE_TIMEOUT_MINUTES = int(os.getenv("SESSION_IDLE_TIMEOUT_MINUTES", "30"))
AUTH_SECRET = os.getenv("AUTH_SECRET", os.getenv("SECRET_KEY", "dev-secret"))

_PASSWORD_HASHER = PasswordHasher()


def _connect() -> sqlite3.Connection:
    Path(AUTH_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.utcnow().isoformat()


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(AUTH_SECRET, salt="itsg33-session")


def init_auth_db() -> None:
    """Initialize the auth database and seed roles."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                force_password_reset INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, role_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (role_id) REFERENCES roles(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                ip TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                action TEXT NOT NULL,
                target TEXT,
                created_at TEXT NOT NULL,
                metadata TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_access (
                assessment_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role_scope TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (assessment_id, user_id)
            )
            """
        )
        conn.commit()
        _seed_roles(conn)
    finally:
        conn.close()


def _seed_roles(conn: sqlite3.Connection) -> None:
    roles = ["admin", "assessor", "client", "viewer"]
    cur = conn.cursor()
    for role in roles:
        cur.execute("INSERT OR IGNORE INTO roles (name) VALUES (?)", (role,))
    conn.commit()


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(hash_value: str, password: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(hash_value, password)
    except VerifyMismatchError:
        return False


def _password_valid(password: str) -> bool:
    if len(password) < 12:
        return False
    common = {"password", "password123", "letmein", "admin", "welcome", "qwerty"}
    return password.lower() not in common


def create_user(email: str, password: str, roles: List[str]) -> Dict[str, Any]:
    if not _password_valid(password):
        raise ValueError("Password does not meet policy")
    conn = _connect()
    try:
        user_id = str(uuid.uuid4())
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (id, email, password_hash, status, created_at, force_password_reset) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, email.lower(), hash_password(password), "active", _now(), 0),
        )
        for role in roles:
            cur.execute("SELECT id FROM roles WHERE name = ?", (role,))
            role_row = cur.fetchone()
            if role_row:
                cur.execute(
                    "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
                    (user_id, role_row["id"]),
                )
        conn.commit()
        user = get_user_by_id(user_id)
        if user is None:
            raise ValueError("Failed to create user")
        return user
    finally:
        conn.close()


def bootstrap_admin() -> None:
    email = os.getenv("INITIAL_ADMIN_EMAIL")
    password = os.getenv("INITIAL_ADMIN_PASSWORD")
    if not email or not password:
        return
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM users")
        row = cur.fetchone()
        if row and row["cnt"] > 0:
            return
    finally:
        conn.close()

    try:
        create_user(email, password, ["admin"])
    except ValueError:
        return


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        row = cur.fetchone()
        if not row:
            return None
        user = dict(row)
        user["roles"] = get_user_roles(user["id"], conn)
        return user
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        user = dict(row)
        user["roles"] = get_user_roles(user_id, conn)
        return user
    finally:
        conn.close()


def list_users() -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users")
        users = []
        for row in cur.fetchall():
            user = dict(row)
            user["roles"] = get_user_roles(user["id"], conn)
            users.append(user)
        return users
    finally:
        conn.close()


def get_user_roles(user_id: str, conn: Optional[sqlite3.Connection] = None) -> List[str]:
    close_conn = False
    if conn is None:
        conn = _connect()
        close_conn = True
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT r.name FROM roles r
            JOIN user_roles ur ON ur.role_id = r.id
            WHERE ur.user_id = ?
            """,
            (user_id,),
        )
        return [row["name"] for row in cur.fetchall()]
    finally:
        if close_conn:
            conn.close()


def create_session(user_id: str, ip: Optional[str], user_agent: Optional[str]) -> str:
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=SESSION_TTL_MINUTES)
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sessions (id, user_id, created_at, expires_at, last_seen, ip, user_agent) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                user_id,
                now.isoformat(),
                expires_at.isoformat(),
                now.isoformat(),
                ip,
                user_agent,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return session_id


def delete_session(session_id: str) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()


def validate_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        if not row:
            return None

        session = dict(row)
        now = datetime.utcnow()
        expires_at = datetime.fromisoformat(session["expires_at"])
        last_seen = datetime.fromisoformat(session["last_seen"])

        if now > expires_at:
            delete_session(session_id)
            return None

        if (now - last_seen).total_seconds() > SESSION_IDLE_TIMEOUT_MINUTES * 60:
            delete_session(session_id)
            return None

        cur.execute("UPDATE sessions SET last_seen = ? WHERE id = ?", (now.isoformat(), session_id))
        conn.commit()
        return session
    finally:
        conn.close()


def sign_session_id(session_id: str) -> str:
    return _serializer().dumps(session_id)


def unsign_session_id(value: str) -> Optional[str]:
    try:
        return _serializer().loads(value)
    except BadSignature:
        return None


def log_audit(
    user_id: Optional[str], action: str, target: Optional[str], metadata: Dict[str, Any]
) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO audit_log (id, user_id, action, target, created_at, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                user_id,
                action,
                target,
                _now(),
                json.dumps(metadata),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def set_user_password(user_id: str, new_password: str, force_reset: bool = False) -> None:
    if not _password_valid(new_password):
        raise ValueError("Password does not meet policy")
    conn = _connect()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, force_password_reset = ? WHERE id = ?",
            (hash_password(new_password), 1 if force_reset else 0, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_user_force_reset(user_id: str, value: bool) -> None:
    conn = _connect()
    try:
        conn.execute(
            "UPDATE users SET force_password_reset = ? WHERE id = ?",
            (1 if value else 0, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_user_roles(user_id: str, roles: List[str]) -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
        for role in roles:
            cur.execute("SELECT id FROM roles WHERE name = ?", (role,))
            role_row = cur.fetchone()
            if role_row:
                cur.execute(
                    "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
                    (user_id, role_row["id"]),
                )
        conn.commit()
    finally:
        conn.close()


def update_last_login(user_id: str) -> None:
    conn = _connect()
    try:
        conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (_now(), user_id))
        conn.commit()
    finally:
        conn.close()


def share_assessment(assessment_id: str, user_id: str, role_scope: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO assessment_access (assessment_id, user_id, role_scope, created_at) VALUES (?, ?, ?, ?)",
            (assessment_id, user_id, role_scope, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def unshare_assessment(assessment_id: str, user_id: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM assessment_access WHERE assessment_id = ? AND user_id = ?",
            (assessment_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_shared_assessment_ids(user_id: str) -> List[str]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT assessment_id FROM assessment_access WHERE user_id = ?",
            (user_id,),
        )
        return [row["assessment_id"] for row in cur.fetchall()]
    finally:
        conn.close()


def user_has_role(user: Dict[str, Any], roles: List[str]) -> bool:
    return any(role in user.get("roles", []) for role in roles)
