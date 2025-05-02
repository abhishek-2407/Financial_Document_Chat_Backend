from typing import TypedDict, Annotated, Literal, List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import AzureChatOpenAI,AzureOpenAIEmbeddings
from langgraph.graph import StateGraph, END
from qdrant_client import QdrantClient
import json
import logging
import os
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore
import qdrant_client
from knowledge_base.rag_functions import embeddings



load_dotenv()

# Initialize Qdrant client

collection_name = "financial_document"

llm = AzureChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("AZURE_OPENAI_KEY"), azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), api_version=os.getenv("AZURE_OPENAI_VERSION"), max_tokens=12000,
                      temperature=0.3,
                      top_p=0.3,)

# Define our state
class AgentState(TypedDict):
    query: str
    context: dict
    retrieval_results: List[Dict]
    agent_outcomes: dict
    current_agent: str
    final_response: str

# Initialize models for our agents
router_llm = llm
revenue_analyst_llm = llm
expense_analyst_llm = llm
profitability_analyst_llm = llm
balance_sheet_analyst_llm = llm
financial_ratio_analyst_llm = llm
comparative_analysis_llm = llm
cxo_llm = llm
synthesizer_llm = llm

def connect_qdrant():
    try:
        client = qdrant_client.QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        
        )
        collection_config = qdrant_client.http.models.VectorParams(
            size=768, 
            distance=qdrant_client.http.models.Distance.COSINE
            )
        
        logging.info("Qdrant client connected successfully.")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to Qdrant: {e}")
        


# Function to retrieve relevant information from Qdrant
def retrieve_from_qdrant(query: str, file_ids: List[str], top_k: int = 100):
    """Retrieve relevant document chunks from Qdrant based on the query"""
    try:
        
      
        
        logging.info(f"top k : {top_k} ")
        client = connect_qdrant()
        vectorstore = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
        )
        
        filter_condition = [
                    qdrant_client.models.FieldCondition(
                        key="metadata.file_id",
                        match=qdrant_client.models.MatchAny(any=file_ids),
                    ),
                    qdrant_client.models.FieldCondition(
                        key="metadata.type",
                        match=qdrant_client.models.MatchValue(value="image"),
                    ),
                       
                ]
        
        # if page_list:
        #     filter_condition.append(
        #         qdrant_client.models.FieldCondition(
        #                 key="metadata.page_number",
        #                 match=qdrant_client.models.MatchAny(any=page_list),
        #             ))
        
        results = vectorstore.similarity_search(
            query,
            k=top_k,
            filter=qdrant_client.models.Filter(
                must=filter_condition,
            ),
        )
        
        # response = {
        #     "status_code": 200,
        #     "message": "success",
        #     "chunks": results,
        # }
        
        formatted_results = []
        for result in results:  # assuming 'results' is a list of Document objects
            formatted_results.append({
                "page_content": result.page_content,
                "metadata": {
                    "file_id": result.metadata.get("file_id", ""),
                    "doc_id": result.metadata.get("doc_id", ""),
                    "file_name": result.metadata.get("file_name", ""),
                    "page_number": result.metadata.get("page_number", ""),
                    "thread_id": result.metadata.get("thread_id", ""),
                },
            })
        
        # print("Response from qdrant",formatted_results)
        return formatted_results

        # return response
        
    
    except Exception as e:
        logging.exception(f"Error retrieving chunks: {e}")
        return  {
            "status_code" : 500,
            "message" : "failed", 
        }

# 1. Router Agent
def router_agent(state: AgentState) -> AgentState:
    """Determines which specialized agent should process the query."""
    
    # First, check if the query is finance-related
    # finance_check_prompt = f"""
    # You are a financial query validator. Determine if the following query is related to finance, financial analysis, 
    # financial documents, or business performance.
    
    # Query: {state['query']}
    
    # Respond with ONLY "yes" if the query is related to finance or "no" if it's not related to finance.
    # """
    
    # finance_check_response = router_llm.invoke([HumanMessage(content=finance_check_prompt)])
    # is_finance_related = finance_check_response.content.lower().strip()
    
    # if "no" in is_finance_related:
    #     # Query is not finance-related, provide a direct response
    #     state["agent_outcomes"] = {}
    #     state["final_response"] = "Please provide a valid financial query."
    #     state["current_agent"] = "end"
    #     return state
    
    # If query is finance-related, proceed with router logic
    router_prompt = f"""
    You are a router agent that analyzes user queries about financial documents and reports.
    Based on the query, determine which specialized agent should handle it.
    
    Query: {state['query']}
    
    Choose ONE of the following agents:
    - revenue_analyst: For queries about revenue analysis, revenue segments, revenue trends, or revenue forecasting
    - expense_analyst: For queries about expense analysis, cost structures, expense trends, or cost optimization
    - comparative_analysis: For queries comparing different aspects, products, time periods, or departments within the organization, trend analysis, or competitive benchmarking
    - summary_agent : For queries about summarizing financial documents only.
    - general_agent: For queries that do not fit into any of the above categories and this also works for calulating financial numbers. Pick this for performing calculation.
    Respond with just the agent name (e.g., "revenue_analyst", "expense_analyst", etc.).
    """
        # - financial_ratio_analyst: For queries about financial ratios, KPIs, liquidity ratios, solvency ratios, or efficiency metrics
    # - profitability_analyst: For queries about profit margins, EBITDA, operating profit, or profitability metrics

    response = router_llm.invoke([HumanMessage(content=router_prompt)])
    
    # Extract agent name from response
    content = response.content.lower().strip()
    logging.info(f"Router response: {content}")
    if "revenue_analyst" in content:
        selected_agent = "revenue_analyst"
    elif "expense_analyst" in content:
        selected_agent = "expense_analyst"
    elif "profitability_analyst" in content:
        selected_agent = "profitability_analyst"
    elif "balance_sheet_analyst" in content:
        selected_agent = "balance_sheet_analyst"
    elif "summary_agent" in content:
        selected_agent = "summary_agent"
    elif "comparative_analysis" in content or "comparative" in content:
        selected_agent = "comparative_analysis"
    elif "general_agent" in content:
        selected_agent = "general_agent"
    elif "cxo" in content:
        selected_agent = "cxo"
    else:
        # Default to revenue analyst if unclear
        selected_agent = "revenue_analyst"
    
    # Update state
    state["agent_outcomes"] = {}
    state["current_agent"] = selected_agent
    
    # Retrieve relevant context from Qdrant
    file_ids = state["context"]["file_id_list"]
    retrieval_results = retrieve_from_qdrant(state['query'], file_ids)
    state["retrieval_results"] = retrieval_results
    
    return state

# 2. Financial Analyst Agent
def revenue_analyst_agent(state: AgentState) -> AgentState:
    """Processes revenue-related queries with deep expertise."""
    
    # Extract context from retrieved documents
    context_text = state["retrieval_results"]
    
    revenue_prompt = f"""
        You are a Revenue Analysis Agent specialized in analyzing revenue performance, trends, and drivers.
        Your goal is to provide deep, insightful, and comparative details about revenue with accurate numerical analysis.

        User Query: {state['query']}

        Context from relevant documents:
        {context_text}

        Instructions:
        1. Focus ONLY on answering what the user has specifically asked about revenue.
        2. Provide comprehensive numerical analysis with exact figures, percentages, and growth rates.
        3. Explain the "why" behind revenue changes with specific business drivers and market factors.
        4. Include relevant calculations to support your analysis (e.g., CAGR, YoY growth, segment contribution).
        5. Present data in tabular format where appropriate to enhance clarity.
        6. For each insight, provide the specific reasoning and evidence from the documents.
        7. Highlight anomalies, patterns, or unexpected trends in the revenue data.
        8. Compare current performance to historical benchmarks when relevant.
        9. Avoid generic statements - every claim should be backed by specific numbers.
        10. Verify all calculations for accuracy before presenting them.

        Do not use fixed headings or a predetermined structure. Instead, organize your response based on what's most relevant to the user's specific query about revenue.

        When creating tables:
        - Include precise numerical data with appropriate units
        - Show comparative data (current vs previous periods)
        - Calculate growth rates and contribution percentages
        - Add a row for insights/comments where appropriate

        Response format:
        - Begin with a direct answer to the user's query
        - Present detailed numerical analysis with supporting calculations
        - Organize information logically based on the specific query
        - Use tables to present complex numerical data clearly (Also have a "Insight" column to provide the reason of "WHY")
        - Conclude with key insights derived from the numerical analysis
        - Provide emojis wherever needed in proper markdown.

        Remember: Focus exclusively on revenue-related information requested by the user. Provide detailed numerical analysis with accurate calculations and clear reasoning.
        """
    
    print("Context text : ",context_text)
    response = revenue_analyst_llm.invoke([HumanMessage(content=revenue_prompt)])
    
    # Update state
    state["agent_outcomes"]["revenue_analyst"] = response.content
    state["current_agent"] = "synthesize"
    
    logging.info("Executed revenue_analyst_agent")
    
    return state

def expense_analyst_agent(state: AgentState) -> AgentState:
    """Processes expense-related queries with deep expertise."""
    
    # Extract context from retrieved documents
    context_text = state["retrieval_results"]
  
    expense_prompt = f"""
        You are an Expense Analysis Agent with expertise in cost structure analysis, expense optimization, and financial efficiency evaluation.

        User Query: {state['query']}

        Context from relevant documents:
        {context_text}
        You are an Expense Analyst Agent.

        Task:
        Analyze the company's expenses for the latest financial year in a highly detailed manner.

        Instructions: (Only provide if Information is available)
        1. Break down total expenses into key categories such as:
        - Employee costs (salaries, benefits, bonuses)
        - Infrastructure and facility costs
        - Marketing and sales expenses
        - Research and Development (R&D) expenses
        - Technology and IT operations costs
        - Other operating and administrative costs
        - Must Include if it exists
        - Any extraordinary or one-time expenses

        2. For each category:
        - Provide the total amount spent
        - Show the percentage contribution to total expenses
        - Compare it with the previous year's data
        - Identify any major increases or decreases and explain the reasons if available

        3. Analyze the impact of overall expenses on:
        - Operating Margin
        - Net Margin
        - Free Cash Flow

        4. Perform benchmarking:
        - Compare the company's expense structure with at least two industry competitors
        - Highlight areas where the company is more/less efficient than competitors

        5. Provide strategic insights:
        - Identify potential cost optimization opportunities
        - Suggest best practices the company can adopt for better cost control

        Output Format:
        - Executive Summary
        - Detailed Expense Breakdown Table
        - Year-over-Year Expense Trend Graphs (if possible)
        - Competitor Benchmarking Table
        - Key Insights and Recommendations
        - Provide emojis wherever needed in proper markdown.

        Important:
        - Keep the analysis objective and backed by data
        - Use clear headings and subheadings
        - Make the output easy to read and actionable.


        """
    
    response = expense_analyst_llm.invoke([HumanMessage(content=expense_prompt)])
    
    # Update state
    state["agent_outcomes"]["expense_analyst"] = response.content
    state["current_agent"] = "synthesize"
    
    logging.info("Executed expense_analyst_agent")
    
    return state

def profitability_analyst_agent(state: AgentState) -> AgentState:
    """Processes profitability-related queries with deep expertise."""
    
    # Extract context from retrieved documents
    context_text = state["retrieval_results"]
    
    profitability_prompt = f"""
    You are a Profitability Analysis Agent specialized in analyzing profit margins, earnings performance, and profitability drivers.
    
    User Query: {state['query']}
    
    Context from relevant documents:
    {context_text}
    
    Instructions: If User ask related to revenue then conduct a comprehensive Profitability analysis covering the following key areas:    
    
    1. MARGIN ANALYSIS:
    - Calculate and analyze gross margin, operating margin, and net profit margin
    - Track margin trends over time and identify inflection points
    - Compare margins across business segments if applicable
    
    2. EARNINGS PERFORMANCE:
    - Analyze EBITDA, operating profit, and net income performance
    - Compare current performance to previous periods
    - Assess quality of earnings and any one-time items affecting profitability
    
    3. PROFITABILITY DRIVERS:
    - Explain changes in profitability metrics (pricing, volume, cost, mix effects)
    - Identify key factors contributing to margin expansion or contraction
    - Analyze the relationship between revenue growth and profit growth
    
    4. MANAGEMENT INSIGHTS:
    - Include management commentary on profitability performance
    - Summarize profitability improvement initiatives
    
    Provide a numbers-rich analysis with proper context and explanation of the "why" behind profitability performance.
    Verify all data to ensure accuracy and avoid any misrepresentations.
    
    Response:
    - Keep the response in a clear, structured format with relevant insights.
    - Include specific numbers and percentages where available.
    - Provide emojis wherever needed in proper markdown.
    """
    
    response = profitability_analyst_llm.invoke([HumanMessage(content=profitability_prompt)])
    
    # Update state
    state["agent_outcomes"]["profitability_analyst"] = response.content
    state["current_agent"] = "synthesize"
    
    logging.info("Executed profitability_analyst_agent")
    
    return state

def general_agent(state: AgentState) -> AgentState:
    """Processes balance sheet-related queries with deep expertise."""
    
    # Extract context from retrieved documents
    context_text = state["retrieval_results"]
    
    balance_sheet_prompt = f"""
    You are a general financial analyst with expertise in reply to user queries which can have calculations.
    User Query: {state['query']}
    
    Context from relevant documents:
    {context_text}
        
    Task: Provide the valid response to user for the query asked based on the documents only. Perform calculations if needed.
    
    Response:
    - Keep the response in a clear, structured format with relevant insights.
    - Include specific numbers and percentages where available.
    - Provide emojis wherever needed in proper markdown.

    """
    
    response = balance_sheet_analyst_llm.invoke([HumanMessage(content=balance_sheet_prompt)])
    
    # Update state
    state["agent_outcomes"]["general_agent"] = response.content
    state["current_agent"] = "synthesize"
    
    logging.info("Executed general_agent")
    
    return state

def summary_agent(state: AgentState) -> AgentState:
    """Processes balance sheet-related queries with deep expertise."""
    
    # Extract context from retrieved documents
    context_text = state["retrieval_results"]
    
    summary_agent_prompt = f"""Must Reply in 9000 words minimum. You are a financial summarizer agent with expertise in analyzing and responding to financial queries..

        USER QUERY: {state['query']}

        CONTEXT FROM RELEVANT DOCUMENTS:
        {context_text}

        TASK:
        Analyze the provided documents and create a comprehensive financial summary addressing the user's query. Adapt your response to focus on the most relevant information available in the context.

        IMPORTANT:
        - Include any other relevant information like geographical growth, talent base, strategic themes and many more if mentioned.
        - Highlight significant pain points, challenges, or risks mentioned in the documents
        - Emphasize unexpected developments or notable changes in business performance
        - Include management's specific comments or outlook on important topics when available.
        - DO NOT REPEAT any metrics or figures already mentioned in the context.
        - Put all the Number you recieved in the "CONTEXT" in the Crisp Points.

        FORMATTING GUIDELINES:
        - Include specific numbers, percentages, and timeframes where available
        - Use bullet points for clarity when appropriate
        - Display the numberic response in Tabular format with insight or calculations as a separate column.
        - Response should be Numeric rich and should not miss any important details.
        - Provide emojis wherever needed in proper markdown.


        Focus on providing the most valuable insights from the available information rather than rigidly following a template.
        """
    
    response = balance_sheet_analyst_llm.invoke([HumanMessage(content=summary_agent_prompt)])
    
    # Update state
    state["agent_outcomes"]["general_agent"] = response.content
    state["current_agent"] = "synthesize"
    
    logging.info("Executed summary_agent")
    
    return state

# 3. Comparative Analysis Agent
def comparative_analysis_agent(state: AgentState) -> AgentState:
    """Conducts comparative analysis across different dimensions."""
    
    # Extract context from retrieved documents
    context_text = ""
    for i, item in enumerate(state["retrieval_results"]):
        context_text += f"\nDocument {i+1}:\n{item['page_content']}\n"
    
    comparative_prompt = f"""
        You are a Comparative Financial Analysis Agent, an expert in analyzing financial statements, industry data, and competitor performance.

        User Query: {state['query']}

        Context extracted from relevant documents:
        {context_text}

        IMPORTANT INSTRUCTIONS:
        1. Answer ONLY the specific question asked by the user - do not provide unrequested information.
        2. Focus on delivering precise, data-driven comparative analysis directly related to the query.
        3. When creating comparison tables:
        - Include a "Reasoning/Analysis" column that explains WHY each entity performs better or worse
        - Highlight the best performer in each metric and explain the specific factors driving their superior performance
        - Use clear numerical data with appropriate units and calculate growth/difference percentages

        For comparative analysis:
        - When comparing to industry benchmarks: Calculate relevant averages and explain deviations
        - When comparing to competitors: Identify specific competitors mentioned in the documents and compare exact metrics
        - When comparing historical performance: Show precise year-over-year changes with calculated growth rates

        Response format:
        1. Begin with a direct, concise answer to the user's specific question
        2. Present detailed comparative tables with:
        - Clear metrics with exact values
        - Calculated percentages or ratios where relevant
        - A "Reasoning" column explaining performance differences
        - Also provide some infomative calulations like growth rates, ratios and many more.
        - Visual indicators (like "↑" or "↓") to show trends
        3. After each table, provide brief insights about the most significant findings

        Example table format:
        | Metric | Company A | Company B | Industry Avg | Best Performer | Reasoning for Performance Difference |
        |--------|-----------|-----------|--------------|----------------|-------------------------------------|
        | Revenue Growth | 12.5% | 8.3% | 9.1% | Company A | Company A's new product line increased market share by 3.2 points |

        Remember:
        - Maintain objectivity and avoid speculation
        - Cite specific evidence from the context for all claims
        - Highlight any data limitations or assumptions made
        - Focus exclusively on answering the user's specific question with comparative data
        - Provide emojis wherever needed in proper markdown.

        """
        
    response = comparative_analysis_llm.invoke([HumanMessage(content=comparative_prompt)])
    
    # Update state
    state["agent_outcomes"]["comparative_analysis"] = response.content
    state["current_agent"] = "synthesize"
    
    logging.info("Executed comparative_analysis_agent")
    
    return state

def cxo_agent(state: AgentState) -> AgentState:
    """Provides executive-level insights and strategic direction."""
    
    # Extract context from retrieved documents
    context_text = ""
    for i, item in enumerate(state["retrieval_results"]):
        context_text += f"\nDocument {i+1}:\n{item['page_content']}\n"
    
    cxo_prompt = f"""
    You are a seasoned C-Suite Executive with extensive experience in strategic leadership, organizational vision, and executive decision-making.
    
    User Query: {state['query']}
    
    Context from relevant documents:
    {context_text}
    
    Provide high-level strategic insights based on the information in the context.
    Focus on:
    - Strategic implications and opportunities
    - Executive-level recommendations
    - Organizational impact and vision
    - Risk assessment and mitigation strategies
    - Market positioning and competitive advantage
    
    Frame your response from an executive perspective, emphasizing strategic direction rather than tactical details.
    Balance short-term considerations with long-term vision.
    If the information provided is insufficient for executive-level guidance, clearly indicate what strategic information would be necessary.
    
    - Provide emojis wherever needed in proper markdown.

    """
    
    response = cxo_llm.invoke([HumanMessage(content=cxo_prompt)])
    
    # Update state
    state["agent_outcomes"]["cxo"] = response.content
    state["current_agent"] = "synthesize"
    
    logging.info("Executed cxo_agent")
    
    return state

# 5. Response Synthesizer
def synthesize_response(state: AgentState) -> AgentState:
    """Formats the response from the specialized agent."""
    
    # Get the active agent and its response
    active_agent = state["current_agent"]
    for agent in ["revenue_analyst", "expense_analyst", "profitability_analyst", 
                 "general_agent","summary_agent", 
                 "comparative_analysis", "cxo"]:
        if agent in state["agent_outcomes"]:
            active_agent = agent
            break
    
    if not active_agent or active_agent not in state["agent_outcomes"]:
        state["final_response"] = "I couldn't determine how to process your query. Please try rephrasing your question."
        state["current_agent"] = "end"
        return state
    
    # Add the response directly
    response = state["agent_outcomes"][active_agent]
    
    state["final_response"] = response
    state["current_agent"] = "end"
    
    return state
# Define the state transition logic
def route_next(state: AgentState) -> Literal["revenue_analyst", "expense_analyst", "profitability_analyst", 
                                           "general_agent","summary_agent",  
                                           "comparative_analysis", "cxo", "synthesize", "end"]:
    return state["current_agent"]

# Build the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("router", router_agent)
workflow.add_node("revenue_analyst", revenue_analyst_agent)
workflow.add_node("expense_analyst", expense_analyst_agent)
workflow.add_node("profitability_analyst", profitability_analyst_agent)
workflow.add_node("general_agent", general_agent)
workflow.add_node("summary_agent", summary_agent)
workflow.add_node("comparative_analysis", comparative_analysis_agent)
workflow.add_node("cxo", cxo_agent)
workflow.add_node("synthesize", synthesize_response)
workflow.add_node("end", lambda x: x)  # Simple pass-through function for the end node

# Add edges
workflow.add_conditional_edges("router", route_next)
workflow.add_conditional_edges("revenue_analyst", route_next)
workflow.add_conditional_edges("expense_analyst", route_next)
workflow.add_conditional_edges("profitability_analyst", route_next)
workflow.add_conditional_edges("general_agent", route_next)
workflow.add_conditional_edges("summary_agent", route_next)
workflow.add_conditional_edges("comparative_analysis", route_next)
workflow.add_conditional_edges("cxo", route_next)
workflow.add_conditional_edges("synthesize", route_next)
workflow.add_edge("end", END)

# Set entry point
workflow.set_entry_point("router")

# Compile the graph
agentic_flow = workflow.compile().with_config({"verbose": True})