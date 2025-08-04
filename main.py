from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn
from dotenv import load_dotenv

from utils.db import Base, engine
from endpoints import router as DocEval
from authorization_endpoints import router as auth_router

load_dotenv()

if len(logging.getLogger().handlers) > 0:
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO)


Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(DocEval, prefix="/doc-eval", tags=["Document Evaluation APIs"])
app.include_router(auth_router, prefix="/auth", tags=["Auth APIs"])

@app.get("/health-check/", status_code=status.HTTP_200_OK)
async def health_check(request: Request):
    return JSONResponse(content={"status": "Healthy"})

if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, workers=3)
