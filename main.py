from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from database import get_db
from auth import authenticate_admin

app = FastAPI()  

app.mount("/static", StaticFiles(directory="static"), name="static")

class AdminLogin(BaseModel):
    username: str
    password: str

@app.post("/admin/login")
async def login_admin(login: AdminLogin, db=Depends(get_db)):
    await authenticate_admin(login.username, login.password, db)
    return {"message": "Вход успешен"}

@app.get("/")
async def root():
    return FileResponse("static/index.html")