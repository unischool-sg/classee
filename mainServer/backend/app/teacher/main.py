from fastapi import FastAPI

from teacher.routers import schedule

app = FastAPI()
app.include_router(schedule.router)
