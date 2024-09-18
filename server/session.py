import json
from base64 import b64encode
from os import urandom
from pathlib import Path

from fastapi import Request, Response
from pydantic import BaseModel, Field

PATH = Path(__file__).parent


class Singleton:
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            print(f"Creating new instance of {cls}")
            cls._instances[cls] = super(Singleton, cls).__new__(cls)
        return cls._instances[cls]


class Database(Singleton):
    def __init__(self):
        self.sessions: dict[str, dict]
        self.clockin: dict[str, list[dict]]
        self.courses: dict[str, dict]

        if not hasattr(self, "sessions"):
            self.sessions = {}
            print("Creating new database")

        if not hasattr(self, "clockin"):
            self.clockin = {}
            print("Creating new database")

        if not hasattr(self, "courses"):
            courses = json.loads((PATH / "courses.json").read_text())
            self.courses = {course["sub_id"]: course for course in courses}

    def get(self, session_id: str):
        return self.sessions.get(session_id, {})

    def update(self, session_id: str, data: dict):
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        self.sessions[session_id].update(data)

    def remove(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]


class ViewState(BaseModel):
    event_target: str = Field("", alias="__EVENTTARGET")
    event_argument: str = Field("", alias="__EVENTARGUMENT")
    view_state: str = Field(..., alias="__VIEWSTATE")
    view_state_generator: str = Field(..., alias="__VIEWSTATEGENERATOR")
    event_validation: str = Field(..., alias="__EVENTVALIDATION")


class Session:
    def __init__(self, request: Request, response: Response):
        self.request = request
        self.response = response
        self.database = Database()
        self.session_id = self.request.cookies.get("ASP.NET_SessionId")

        self.new_session = False
        if not self.session_id:
            print("Creating new session")
            self.session_id = urandom(12).hex()
            self.new_session = True

    def login(self, username: str, password: str):
        if username.startswith("D") and password == "password":
            self.db_update({"login": True, "username": username})
            return True

    def db_get(self, key: str):
        return self.database.get(self.session_id).get(key)

    def db_update(self, data: dict):
        self.database.update(self.session_id, data)

    def get_clockin(self):
        username = self.db_get("username")
        return self.database.clockin.get(username, [])

    def add_clockin(self, data: dict):
        username = self.db_get("username")
        if username not in self.database.clockin:
            self.database.clockin[username] = []
        self.database.clockin[username].append(data)

    def verify_login(self):
        sess = self.database.get(self.session_id)
        return sess.get("login", False)

    def create_view_state(self, path: str):
        view_state = ViewState(
            __EVENTTARGET="",
            __EVENTARGUMENT="",
            __VIEWSTATE=b64encode(urandom(128)).decode(),
            __VIEWSTATEGENERATOR=urandom(4).hex().upper(),
            __EVENTVALIDATION=b64encode(urandom(128)).decode(),
        )

        self.database.update(
            self.session_id,
            {
                "path": path,
                "view_state": view_state.model_dump(by_alias=True),
            },
        )

        return view_state

    async def verify_view_state(self, path: str):
        sess = self.database.get(self.session_id)
        if sess.get("path", "") != path:
            return False

        view_state = ViewState(**sess.get("view_state", {}))
        form_data = ViewState(**(await self.request.form()))
        print(view_state == form_data)
        if view_state != form_data:
            return False

        return True

    def headers(self):
        if self.new_session:
            return {"Set-Cookie": f"ASP.NET_SessionId={self.session_id}; Path=/; HttpOnly; SameSite=Lax"}
