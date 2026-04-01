from fastapi import FastAPI
from core.config import settings

app = FastAPI(title="ParaEarth Orchestration Service", version="1.0.0")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "orchestration"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)