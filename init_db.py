import asyncio
import asyncpg
import bcrypt
from dotenv import load_dotenv
import os

load_dotenv()

async def init_db():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL
            );
        """)
        admin = await conn.fetchrow("SELECT * FROM admins WHERE username = $1", "admin")
        if not admin:
            hashed_password = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
            await conn.execute(
                "INSERT INTO admins (username, password_hash) VALUES ($1, $2)",
                "admin", hashed_password
            )
    finally:
        await conn.close()

asyncio.run(init_db())