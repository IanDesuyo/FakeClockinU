from datetime import datetime, timedelta
from pathlib import Path

import jwt
from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import server.model as model

from .session import Database, Session

PATH = Path(__file__).parent

JWT_KEY = "CCU_SUPER_SECRET"
JWT_EXP_SECONDS = 20

app = FastAPI()
templates = Jinja2Templates(directory=PATH / "templates")


@app.middleware("http")
async def case_sens_middleware(request: Request, call_next):
    path = request.scope["path"].lower()
    request.scope["path"] = path

    response = await call_next(request)
    return response


app.mount("/clockin/content", StaticFiles(directory=PATH / "public" / "Content"), name="Content")
app.mount("/clockin/scripts", StaticFiles(directory=PATH / "public" / "Scripts"), name="Scripts")
app.mount("/clockin/img", StaticFiles(directory=PATH / "public" / "img"), name="img")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return RedirectResponse(url=f"/clockin/Error.aspx?msg={str(exc)}", status_code=302)


@app.get("/")
async def root():
    return RedirectResponse(url="/clockin/login.aspx")


@app.get("/clockin/error.aspx")
async def error(request: Request, msg: str = Query(None)):
    return templates.TemplateResponse("error.html", {"request": request, "msg": msg})


@app.get("/clockin/login.aspx")
async def login(request: Request, session: Session = Depends()):
    view_state = session.create_view_state("/clockin/login.aspx")

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "view_state": view_state},
        headers=session.headers(),
    )


@app.post("/clockin/login.aspx")
async def login_callback(request: Request, session: Session = Depends(), data: model.LoginModel = Depends()):
    if not await session.verify_view_state("/clockin/login.aspx"):
        return RedirectResponse(url="/clockin/Error.aspx?msg=ViewState%20%E9%8C%AF%E8%AA%A4", status_code=302)

    success = session.login(data.username, data.password)

    if success:
        return RedirectResponse(url="/clockin/Student.aspx", status_code=302)

    view_state = session.create_view_state("/clockin/login.aspx")

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "view_state": view_state, "error": "您的登入嘗試失敗。請再試一次。"},
        headers=session.headers(),
    )


@app.get("/clockin/student.aspx")
async def student(request: Request, session: Session = Depends()):
    # This page doesn't check login state
    view_state = session.create_view_state("/clockin/Student.aspx")

    return templates.TemplateResponse(
        "student.html",
        {"request": request, "view_state": view_state},
        headers=session.headers(),
    )


@app.post("/clockin/student.aspx")
async def student_callback(request: Request, session: Session = Depends(), data: model.StudentModel = Depends()):
    # This page doesn't check login state
    if not await session.verify_view_state("/clockin/Student.aspx"):
        return RedirectResponse(url="/clockin/Error.aspx?msg=ViewState%20%E9%8C%AF%E8%AA%A4", status_code=302)

    if data.button == "學生課堂打卡":
        return RedirectResponse(url="/clockin/ClassClockin.aspx", status_code=302)

    return RedirectResponse(
        url="/clockin/Error.aspx?msg=%E4%BD%A0%E7%94%A8%E4%B8%8D%E5%88%B0%E9%80%99%E5%8A%9F%E8%83%BD", status_code=302
    )


@app.get("/clockin/classclockin.aspx")
async def class_clockin(request: Request, session: Session = Depends(), param: str = Query(None)):
    if not session.verify_login():
        return RedirectResponse(url="/clockin/Error.aspx?msg=%E6%9C%AA%E7%99%BB%E5%85%A5", status_code=302)

    error = None
    if param:
        # Handle QR code
        try:
            data = jwt.decode(param, JWT_KEY, algorithms=["HS256"])

            courses = session.database.courses
            session.add_clockin(
                {
                    "course": courses[data["sub_id"]]["sub_name"],
                    "period": 1,
                    "time": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                }
            )
        except Exception as e:
            error = f"QRcode錯誤，請重新掃描\n({e})"

    view_state = session.create_view_state("/clockin/ClassClockin.aspx")

    student = session.db_get("username")
    clockins = session.get_clockin()

    return templates.TemplateResponse(
        "class_clockin.html",
        {"request": request, "view_state": view_state, "student": student, "clockins": clockins, "error": error},
        headers=session.headers(),
    )


@app.get("/clockin/qrcodescanner.aspx")
async def qr_code_scanner(request: Request, session: Session = Depends()):
    # This page doesn't check login state

    return templates.TemplateResponse(
        "qr_code_scanner.html",
        {"request": request},
        headers=session.headers(),
    )


@app.get("/qrcode")
async def qr_code(request: Request, sub_id: str = Query(None)):
    db = Database()
    courses = db.courses

    course = courses.get(sub_id, None)

    qrcode = ""
    if course:
        current = datetime.now()
        qrcode = jwt.encode(
            {
                "cls_id": course["cls_id"],
                "sub_id": course["sub_id"],
                "scr_dup": course["scr_dup"],
                "yms_year": "112",
                "yms_smester": "2",
                "period": "1",
                "timestamp": current.isoformat(timespec="seconds"),
                "exp": int((current + timedelta(seconds=JWT_EXP_SECONDS)).timestamp()),
            },
            JWT_KEY,
        )

    return templates.TemplateResponse(
        "qrcode.html",
        {
            "request": request,
            "course": course,
            "courses": courses.values(),
            "qrcode": qrcode,
        },
    )


@app.get("/debug")
async def debug(request: Request):
    db = Database()
    return {"session": db.sessions, "clockin": db.clockin, "courses": db.courses}
