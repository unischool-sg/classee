from fastapi import FastAPI

from teacher.routers import auth, schedule

app = FastAPI()
app.include_router(auth.router)
app.include_router(schedule.router)
