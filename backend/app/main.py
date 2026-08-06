from fastapi import FastAPI

app = FastAPI(title="VoyageAI API")


@app.get("/")
def root():
    return {"message": "VoyageAI Backend Running 🚀"}