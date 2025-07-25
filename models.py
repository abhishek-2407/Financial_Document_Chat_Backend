from sqlalchemy import Column, String, Boolean, DateTime, MetaData, Table, text, Enum,JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

import uuid

Base = declarative_base()

class UserS3Mapping(Base):
    __tablename__ = 'user_s3_mapping'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=True)
    s3_file_url = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    modified_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    cluster_id = Column(String, nullable=False)
    file_id = Column(String, nullable=True)
    thread_id = Column(String, nullable=True)
    active_file = Column(Boolean, nullable=True, default=True)
    folder_name = Column(String, nullable=True)
    rag_status = Column(Boolean, default=False)


class User(Base):
    __tablename__ = "user"
    email = Column(String, primary_key=True, index=True)
    password = Column(String)  # hashed password
    access_token = Column(String, nullable=True)
    access_token_creation_datetime = Column(DateTime, nullable=True)
    role = Column(String, default="user")
    
class RoleEnum(str, enum.Enum):
    master_admin = "super_admin"
    admin = "admin"
    user = "user"

class UserInvite(Base):
    __tablename__ = "user_invite"

    email = Column(String, primary_key=True, index=True)
    role = Column(Enum(RoleEnum, name="role_enum"), nullable=False)
    invited = Column(Boolean, default=False)
 
class ReportStatus(str, enum.Enum):
    inprogress = "inprogress"
    completed = "completed"

class SummaryReport(Base):
    __tablename__ = "summary_report"

    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    s3_url = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    status = Column(Enum(ReportStatus), default=ReportStatus.inprogress, nullable=False)
    source_file_id = Column(JSON, nullable=False)  # Assumes a list of UUIDs
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None) 
    
    
class FileAttribute(Base):
    __tablename__ = "files_attribute"

    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generated_section = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
   
