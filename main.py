import os
import logging
import uvicorn

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import endpoints as DocEval


load_dotenv()

if len(logging.getLogger().handlers) > 0:
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO)


# main.py
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from models import Base

# Configure your database connection
DATABASE_URL = os.getenv("DB_URI")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables on startup if they don't exist
Base.metadata.create_all(bind=engine)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Your FastAPI routes follow...
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(
    DocEval.router,
    prefix="/doc-eval",
    tags=["Document Evaluation APIs"]
)

@app.get("/health-check/", status_code=status.HTTP_200_OK)
async def health_check(request: Request):
    return JSONResponse(content={"status": "Healthy"})


if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0",port=8000, reload=True)