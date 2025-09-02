import uvicorn

from fastapi import FastAPI
from src.router.router import apirouter


app = FastAPI()

app.include_router(apirouter, prefix="/api")


def main():
    print("Hello from api-service!")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
