import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.middleware.logger_middleware import LoggingMiddleware
from src.router.router import apirouter

origins = [
    "https://klhk-budget-preclearance.vercel.app",
    "http://localhost:8080",
]


app = FastAPI()
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(apirouter, prefix="/api")


def main():
    print("Hello from api-service!")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
