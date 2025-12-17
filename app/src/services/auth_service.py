from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    email: str
    name: Optional[str] = None


class AuthError(Exception):
    pass


class AuthService:
    def signup(self, email: str, password: str, consent: bool):
        email = (email or "").strip()
        password = (password or "").strip()

        if not email or not password or not consent:
            raise AuthError("All the fields are mandatory.")

        # TODO(later):
        # register the user

        return User(email=email)
    
    def login(self, email: str, password: str) -> User:
        email = (email or "").strip()
        password = (password or "").strip()

        if not email or not password:
            raise AuthError("Email and password are required.")

        # TODO (later):
        #   Replace this stub with a secure API call to your cloud backend, e.g.:
        #
        #   response = requests.post(
        #       f"{BASE_URL}/auth/login",
        #       json={"email": email, "password": password},
        #       timeout=10,
        #   )
        #   if response.status_code != 200:
        #       raise AuthError("Invalid email or password.")
        #   data = response.json()
        #   return User(email=data["email"], name=data.get("name"))
        #
        # For now we just accept any non-empty credentials:
        return User(email=email, name=None)