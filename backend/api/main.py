from fastapi import FastAPI

app = FastAPI(title="PramanaGST API")

@app.get("/")
def read_root():
    return {"message": "PramanaGST API Running"}
