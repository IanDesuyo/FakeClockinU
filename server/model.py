from dataclasses import dataclass

from fastapi import Form


@dataclass
class ViewState:
    event_target: str = Form("", alias="__EVENTTARGET")
    event_argument: str = Form("", alias="__EVENTARGUMENT")
    view_state: str = Form("", alias="__VIEWSTATE")
    view_state_generator: str = Form("", alias="__VIEWSTATEGENERATOR")
    event_validation: str = Form("", alias="__EVENTVALIDATION")


@dataclass
class LoginModel(ViewState):
    username: str = Form(..., alias="LoginLdap$UserName")
    password: str = Form(..., alias="LoginLdap$Password")
    button: str = Form(..., alias="LoginLdap$LoginButton")

@dataclass
class StudentModel(ViewState):
    button: str = Form(..., alias="ButtonClassClockin")