from fastapi import FastAPI

app = FastAPI()

@app.get("/echo")
def echo():
    return {"message": "Hello, World!"}

@app.get("/echo/{name}")
def echo_name(name: str):
    return {"message": f"Hello, {name}!"}
