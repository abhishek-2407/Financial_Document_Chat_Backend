

from utils.llm_calling import call_openai

def get_router_response(user_query: str) -> str:
    
    system_prompt = """
    You are a router agent that analyzes user queries about financial documents and reports.
    Based on the query, determine which specialized agent should handle it.
    
    Choose ONE or mutiple if required of the following agents:
    - revenue_analyst: For queries about revenue analysis, revenue segments, revenue trends, or revenue forecasting
    - expense_analyst: For queries about expense analysis, cost structures, expense trends, or cost optimization
    - comparative_analysis: For queries comparing different aspects, products, time periods, or departments within the organization, trend analysis, or competitive benchmarking
    - summary_agent : For queries about summarizing financial documents only.
    - general_agent: For queries that do not fit into any of the above categories and this also works for calulating financial numbers. Pick this for performing calculation.
    Respond with just the agent name in list(e.g., [ {"agent" : "revenue_analyst", "prompt" : "Independant prompt for this agent, do not anything more "}, {"agent" : "expense_analyst", "prompt" : "Independant prompt for this agent, do not anything more "}, etc ]).
    """
    
    
    user_prompt = f"This is user query: {user_query}"
    
    response = call_openai(system_prompt=system_prompt, user_prompt=user_prompt)
    
    return response