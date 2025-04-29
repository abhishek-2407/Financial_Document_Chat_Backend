
class DatabaseError(Exception):
    """Exception raised for database-related errors"""
    pass

class VectorDBError(Exception):
    """Exception raised for vector database operation errors"""
    pass

class S3Error(Exception):
    """Exception raised for S3 operation errors"""
    pass

class FileOperationError(Exception):
    """Exception raised for general file operation failures"""
    pass