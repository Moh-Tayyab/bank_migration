import uvicorn
from api_only import app


def main():
    uvicorn.run("api_only:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
