import logging
from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import String, any_, delete, select
from sqlalchemy.orm import Session

from models import TestCase, UserS3Mapping
from utils.postgres_connection import ConnectDB
from utils.db import engine, get_db

router = APIRouter()

class UserS3MappingMinimalSchema(BaseModel):
    id: str
    file_name: str

    class Config:
        orm_mode = True 

class TestCaseSchema(BaseModel):
    id: uuid.UUID
    file_id_list: List[str]
    prompt: str
    expected_output: str
    files: List[UserS3MappingMinimalSchema] = []

    class Config:
        orm_mode = True

@router.get("/", response_model=List[TestCaseSchema])
async def get_files(session: Session = Depends(get_db)):
    response = session.execute(select(TestCase)).scalars().all()
    # for res in response:
        # data = session.execute(select(UserS3Mapping).where(UserS3Mapping.id.in_(file for file in TestCase.file_id_list))).scalars().all()
        # print(data)
        # res.files = [
        #     UserS3MappingMinimalSchema(
        #         id=str(file.id),
        #         file_name=str(file.file_name),
        #     ) for file in data
        # ]
    return response

class TestCaseCreate(BaseModel):
    file_id_list: List[str]
    prompt: str
    expected_output: str

@router.post("/")
async def insert_testcase(testcase: TestCaseCreate, session: Session = Depends(get_db)):
    case = TestCase(**testcase.model_dump())
    session.add(case)
    session.commit()
    session.refresh(case)
    return case

@router.delete("/{id}")
async def delete_testcase(id: uuid.UUID, session: Session = Depends(get_db)):
    testcase = session.get(TestCase, id)
    if not testcase: raise HTTPException(404, "Couldn't find testcase")

    session.execute(delete(TestCase).where(TestCase.id == testcase.id))
    session.commit()

    return "Deleted testcase"
        
@router.get("/{id}")
async def get_final_files(id: str):
    query = """Select file_name, s3_file_url, file_id, thread_id, folder_name, rag_status from user_s3_mapping where deleted_at is NULL and rag_status is true;"""
    db = ConnectDB()
    try:
        response = db.fetch(query=query)
        
        return response
        
    except Exception as e:
        return {
             "status_code" : 500,
             "error" : e
         }
        
    finally : 
        db.close_connection()
    

