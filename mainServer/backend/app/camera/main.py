from fastapi import FastAPI

from camera.routers import schedule, videos

app = FastAPI()
app.include_router(videos.router)
app.include_router(schedule.router)
