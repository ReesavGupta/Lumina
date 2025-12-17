import os
import json
import requests
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

API_BASE_URL = os.getenv("LUMINA_API_BASE_URL", "http://localhost:8080")
SESSION_FILE = Path.home() / ".lumina_session.json"

@dataclass
class User:
    email: str
    name: Optional[str] = None
    token: Optional[str] = None

class AuthError(Exception):
    pass

class AuthService:
    """desktop side auth service"""
    def _save_session(self, user: User) -> None:
        data = {
            "email": user.email,
            "name": user.name,
            "token": user.token,
        }
        SESSION_FILE.write_text(json.dumps(data))

    def load_session(self) -> Optional[User]:
        if not SESSION_FILE.exists():
            return None
        try:
            data = json.loads(SESSION_FILE.read_text())
            return User(
                email=data.get("email", ""),
                name=data.get("name"),
                token=data.get("token"),
            )
        except Exception:
            return None

    def clear_session(self) -> None:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

    def signup(self, email: str, password: str, consent: bool) -> User:
        email = (email or "").strip()
        password = (password or "").strip()

        if not email or not password or not consent:
            raise AuthError("All fields are mandatory and consent is required.")

        try:
            resp = requests.post(
                f"{API_BASE_URL}/auth/signup",
                json={
                    "email": email,
                    "password": password,
                    "full_name": None,
                    "consent": consent,
                },
                timeout=10,
            )
        except requests.RequestException:
            raise AuthError("Unable to reach server. Please check your connection.")

        if resp.status_code != 201:
            msg = resp.json().get("detail", "Signup failed.")
            raise AuthError(str(msg))

        return User(email=email)
    
    def login(self, email: str, password: str) -> User:
        email = (email or "").strip()
        password = (password or "").strip()

        if not email or not password:
            raise AuthError("Email and password are required.")

        try:
            resp = requests.post(
                f"{API_BASE_URL}/auth/login",
                data={"username": email, "password": password},
                timeout=10,
            )
        except requests.RequestException:
            raise AuthError("Unable to reach server. Please check your connection.")

        if resp.status_code != 200:
            msg = resp.json().get("detail", "Invalid email or password.")
            raise AuthError(str(msg))

        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise AuthError("Login response did not include a token.")

        user = User(email=email, token=token)
        self._save_session(user)
        return user