from fastapi import FastAPI
from db import get_db

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}