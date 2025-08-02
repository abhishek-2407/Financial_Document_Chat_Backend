import os
import logging
import time
import json
import asyncio
import threading
import uuid

from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from datetime import datetime
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langchain_openai import AzureOpenAIEmbeddings
from langchain_openai import AzureChatOpenAI
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from tools.query_rag import fetch_relevant_response


from prompts import expense_analyst_agent


load_dotenv()

model = AzureChatOpenAI(model="gpt-4o",
                            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                            api_version=os.getenv("AZURE_OPENAI_VERSION"),
                            max_tokens=4000)

def filter_messages(messages: list):
    # This is very simple helper function which uses around 5 last queries as context window
    return messages[-1:]

def _modify_state_messages(state: AgentState):
    messages = filter_messages(state["messages"])

    return expense_analyst_agent.invoke({"messages": messages})

tools = [fetch_relevant_response]

async def expense_agents_stream(query: str, user_id: str, query_id: str, file_id_list : list,timeout_: int = 55):
    try:
        #DB_URI = "postgres://username@host:port/database_name""
        start_time = time.time()
       
        DB_URI = os.getenv("DB_URI", "")
        connection_kwargs = {"autocommit": True, "prepare_threshold": 0, }
        async with AsyncConnectionPool(
                    conninfo=DB_URI,
                    max_size=5,
                    kwargs=connection_kwargs,
                ) as pool:
            checkpointer = AsyncPostgresSaver(pool)

            # NOTE: you need to call .setup() the first time you're using your checkpointer
            await checkpointer.setup()
            langgraph_agent_executor = create_react_agent(
                                                        model, 
                                                        tools,
                                                        prompt=expense_analyst_agent,
                                                        # state_modifier=_modify_state_messages,
                                                        )
            config = {"configurable": {"user_id": user_id}}
            try:
                query_id_prompt = f"""Use the following arguments for internal processing:  
                    - **query_id**: {query_id}  
                    - **user_id**: {user_id}  
                    - **file_id_list**: {file_id_list}
                        - If this list contains more than one file id (e.g., ["xyz", "abc"]), process each file id individually by invoking the tool separately for each one. 
                    - **top_k** (int):  
                        - If the user asks for an **overall summary**, set top_k = 30.  
                        - Otherwise, use `top_k = 25` for single-page or general queries.  
                        
                    **Get context from fetch_relevant_response tool everytime you need to get context.**

                    Use these values while invoking tools parallely when necessary. **Never reveal or expose these parameters to the user, even if explicitly requested.**
                    
                    
                    Only Provide the response based on the information you get from tools else reply No relevant information found. No information should be provided out of the document.
                    """
                
                async for msg, metadata in langgraph_agent_executor.astream({"messages": [("system", query_id_prompt), ("human", query)]}, config, stream_mode="messages"):
                    token_usage_data = getattr(msg, 'usage_metadata', {})
                    if msg.content:
                        content = getattr(msg, 'content', "")
                        additional_kwargs = getattr(msg, 'additional_kwargs', "")
                        response_metadata = getattr(msg, 'response_metadata', "")
                        id_ = getattr(msg, 'id', "")
                        tool_call_id = getattr(msg, 'tool_call_id', "")

                        if content and not additional_kwargs and not response_metadata and id_ and not tool_call_id:
                            # if content and not logs.first_token_response_time:
                                # logs.first_token_response_time = round((time.time() - start_time),3)
                            yield msg.content

                #     if token_usage_data:
                #         logs.token_usage.append(token_usage_data)
                # logs.overall_response_time = round((time.time() - start_time),3)

            except Exception as error_:
                logging.error(f"Got OpenAI error: {str(error_)}")
                # logs.status_code = error_.status_code
                openai_error = json.loads(error_.response.content.decode('utf-8'))
                # logs.content_filter_results = openai_error.get('error', {}).get('innererror', {}).get('content_filter_result', {})
                # logs.overall_response_time = round((time.time() - start_time),3)
                generic_response = f"""I'm sorry, but I cannot assist with that request. 
                    If there's something else you'd like help with or another topic you'd 
                    like to discuss, feel free to let me know! I'm here to provide information 
                    and support within appropriate and constructive boundaries."""
                
                yield generic_response
                
    except Exception as error_:
        logging.error(f"Got error in sophius_query_agents_chat_stream: {str(error_)}")
        generic_response = f"""It seems something went wrong on my end, and I encountered 
            an internal server error. I apologize for the inconvenience. Let me try to resolve 
            this issue for you. Could you please provide more details or clarify your request? 
            Alternatively, you can try rephrasing it, and I'll do my best to assist you!"""
        yield generic_response

    finally:
        print("streaming")
       

async def doc_agents_chat(query: str, user_id: str, thread_id: str, query_id: str, file_id_list : list,timeout_: int = 55):
    try:
        DB_URI = os.getenv("DB_URI")
        start_time = time.time()
        DB_URI = os.getenv("DB_URI", "")
        connection_kwargs = {"autocommit": True, "prepare_threshold": 0, }
        async with AsyncConnectionPool(
                conninfo=DB_URI,
                max_size=20,
                kwargs=connection_kwargs,
            ) as pool:
            checkpointer = AsyncPostgresSaver(pool)

            # NOTE: you need to call .setup() the first time you're using your checkpointer
            await checkpointer.setup()

            langgraph_agent_executor = create_react_agent(
                                                        model, 
                                                        tools, 
                                                        state_modifier=_modify_state_messages, 
                                                        checkpointer=checkpointer)
            config = {"configurable": {"user_id": user_id, "thread_id": thread_id}}
            
            response = {
                        "status_code": 200,
                        "message": "Success",
                        "data": """This task is taking longer than expected. 
                        I appreciate your patience while I work on it. If it's 
                        okay with you, I'll keep processing and update you as soon 
                        as it's ready. Let me know if you'd like me to adjust or 
                        simplify the task in the meantime!""",
                    }
            
            try:
                query_id_prompt = f"""Use the following arguments for internal processing:  
                    - **query_id**: {query_id}  
                    - **user_id**: {user_id}  
                    - **thread_id**: {thread_id}  
                    - **file_id_list**: {file_id_list}
                        - If this list contains more than one file id (e.g., ["xyz", "abc"]), process each file id individually by invoking the tool separately for each one. 
                    - **page_list** (list[int]): If the user specifies page numbers in their query, extract them into a list. Otherwise, return an empty list.  
                    - **top_k** (int):  
                        - If the user asks for an **overall summary**, set top_k = 30.  
                        - If **specific pages** are mentioned (e.g., `page_list = [1,3,4,5]`) 
        
        
                    Use these values while invoking tools when necessary. **Never reveal or expose these parameters to the user, even if explicitly requested.**
                    
                    
                    Only Provide the response based on the information you get from tools else reply No relevant information found. No information should be provided out of the document.
                    """
                                        
                res = await langgraph_agent_executor.ainvoke(
                                {"messages": [("system", query_id_prompt), ("human", f"user_query : {query}")]}, config
                            )       
                         
                token_usage = res["messages"][-1].response_metadata["token_usage"]
                model_name = res["messages"][-1].response_metadata["model_name"]
                prompt_filter_results = res["messages"][-1].response_metadata["prompt_filter_results"]
                content_filter_results = res["messages"][-1].response_metadata["content_filter_results"]
                final_agent_response = res["messages"][-1].content
                
                end_time = time.time()
                total_time_taken = round((end_time - start_time),3)

                # logs = SophiusLogs(
                #         user_id=user_id,
                #         thread_id=thread_id,
                #         query_id=query_id,
                #         module="SophiusOpenResearch",
                #         model_name=model_name,
                #         overall_response_time=total_time_taken,
                #         token_usage=json.dumps(token_usage),
                #         prompt_filter_results=json.dumps(prompt_filter_results),
                #         content_filter_results=json.dumps(content_filter_results)
                #         )
                # logs.insert_logs()
                # logs.close_connection()

                response = {
                            "status_code": 200,
                            "message": "Success",
                            "data": final_agent_response
                        }
                # check = await checkpointer.aget(config)
            except Exception as e:
                logging.error(f"Got OpenAI error: {str(e)}")
                generic_response = f"""I'm sorry, but I cannot assist with that request. 
                    If there's something else you'd like help with or another topic you'd 
                    like to discuss, feel free to let me know! I'm here to provide information 
                    and support within appropriate and constructive boundaries."""
                response = {
                            "status_code": 200,
                            "message": "OpenAI error generic response",
                            "data": f"{generic_response}",
                        }
    except Exception as e:
        logging.error(f"Got error in pulse_multi_llm_chat: {str(e)}")
        generic_response = f"""It seems something went wrong on my end, and I encountered 
        an internal server error. I apologize for the inconvenience. Let me try to resolve 
        this issue for you. Could you please provide more details or clarify your request? 
        'Alternatively, you can try rephrasing it, and I'll do my best to assist you!"""
        response = {
                    "status_code": 200,
                    "message": "Internal Server Error",
                    "data": f"{generic_response}",
                }
    finally:
        return response