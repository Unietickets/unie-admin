from fastapi import HTTPException, status
import bcrypt

async def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

async def authenticate_admin(username: str, password: str, db):
    admin = await db.fetchrow("SELECT * FROM admins WHERE username = $1", username)
    if not admin or not await verify_password(password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return admin