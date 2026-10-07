from fastapi import FastAPI

from teacher.routers import auth, classrooms, devices, schedule, users

app = FastAPI()
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(classrooms.router)
app.include_router(devices.router)
app.include_router(schedule.router)
