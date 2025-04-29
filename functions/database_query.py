import os
import logging
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from utils.postgres_connection import ConnectDB
from utils.llm_calling import call_openai
from langchain_core.tools import tool

if len(logging.getLogger().handlers) > 0:
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO)

load_dotenv()

@tool
async def get_sql(user_query: str, user_id: str) -> str:
    """
    Converts the user message to an appropriate SQL query, which would be able to fetch the required data from the Database.
    
    Args:
    user_query (str) - The message sent by the user, to the chatbot
    user_id - uuid from the fronted to identify user

    Returns:

        str: an SQL query that would help fetch the required info
    
    """

    database_structure = """CREATE TABLE users (
                user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  
                first_name VARCHAR(50),
                last_name VARCHAR(50),
                email VARCHAR(100) UNIQUE,
                phone_number VARCHAR(15) UNIQUE,
                balance NUMERIC(12, 2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            

CREATE TABLE amounts (
                amount_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  
                amount NUMERIC(12, 2),
                currency VARCHAR(3),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
CREATE TABLE transactions (
                transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  
                user_id UUID REFERENCES users(user_id),  
                amount_id UUID REFERENCES amounts(amount_id),  
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                transaction_type VARCHAR(10) CHECK (transaction_type IN ('credit', 'debit')),
                status VARCHAR(20) CHECK (status IN ('failed', 'paid', 'on hold')),
                source_name VARCHAR(100),
                destination_name VARCHAR(100),
                payment_mode VARCHAR(20) CHECK (payment_mode IN ('card', 'UPI', 'netbanking')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """

 
    try:
    
        system_template = f"""
            You are a PostgreSQL expert. 
            Given an input question from the user, create a syntactically correct PostgreSQL query and return ONLY the generated query, nothing else.

            Always keep user_id as the filter in the query with a value of user_id = '{user_id}'.

            History:
            If you do not fully understand the prompt, take hints from the "History" of questions the user has asked.
            {database_structure}

            NOTE: ---INCLUDE TRANSACTION ID if asked, DO NOT INCLUDE USER ID OR AMOUNT ID IN THE RESULT, all the amounts are in GBP---
        """
        
        user_template = f"""user_query : {user_query}"""

        sql_query = call_openai(system_prompt=system_template, user_prompt=user_template)
        # Create a chain that passes the prompt to the LLM and parses the result

        
        sql_query = sql_query.replace("```sql", "").replace("```", "")
        db = ConnectDB()
        
        logging.info(f"Generated SQL Query: {sql_query}")
        response = db.fetch(sql_query)

        logging.info("SQL query executed successfully.")

        return response

    except ValueError as ve:
        logging.error(f"Tenant selection error: {ve}")
        raise ve

    except Exception as e:
        logging.error(f"Error during SQL query generation or execution: {e}")
        raise e
    
    finally:
        db.close_connection()