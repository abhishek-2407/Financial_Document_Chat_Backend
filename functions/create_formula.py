from pydantic import BaseModel, Field
from langchain_openai import AzureChatOpenAI
import os 
from dotenv import load_dotenv
import logging
import re

load_dotenv()

def get_data(word: str) -> float:
    sample_data = {
        "EBIT": 1000,
        "Tax Rate": 0.3,
        "Depreciation": 200,
        "Change in Working Capital": 50,
        "Capital Expenditures": 300,
        "Net Income" : 488,
        "Non-Cash Charges" : 847,
        "Interest" : 7346
    }
    # sample_data = {
    #     EBIT = $500 million
    # Tax Rate = 30%
    # Depreciation & Amortization = $60 million
    # CapEx = $120 million
    # ΔNWC = $40 million
    # }
    return sample_data.get(word, 0)


def evaluate_formula(result_json: dict):
    formula = result_json["formula"]
    keywords = [k.strip() for k in result_json["keywords_used"].split(",")]

    evaluated_formula = formula
    for keyword in sorted(keywords, key=len, reverse=True): 
        value = get_data(keyword)
        evaluated_formula = re.sub(rf"\b{re.escape(keyword)}\b", str(value), evaluated_formula)

    print("Original Formula:", formula)
    print("Evaluated Formula:", evaluated_formula)

    try:
        result = eval(evaluated_formula, {"__builtins__": {}})
    except Exception as e:
        result = f"Error in evaluation: {e}"

    return result

def create_formula(user_query, previous_formula: str = None):
    class GetFormula(BaseModel):
        formula: str = Field(
            description=(
                "You are a Financial Formula Creator.\n"
                f"This is user_query: {user_query}\n\n"
                "- Analyse the user query carefully.\n"
                "- Generate only the **mathematical formula expression** that answers the query.\n"
                "- Do NOT prepend variable names like 'FCFF =' or 'ROE ='.\n"
                "- Do NOT include '=' anywhere. Just return the expression.\n"
                "- If the formula has numerator and denominator, write them together (e.g., 'Net Profit / Shareholder’s Equity').\n"
                "- Ensure the formula is correct, clear, and complete.\n"
                f"If previous_formula : {previous_formula}, then provide the alternative and elobarated formula for the user_query."
            )
        )  

        numerator_formula: str = Field(
            description=(
                "Provide only the **entire numerator part** of the formula.\n"
                "- Do NOT include denominator, '=' or any extra explanation.\n"
                "- If the formula has no numerator (e.g., it's just a single value), return the whole formula.\n"
                f"If previous_formula : {previous_formula}, then provide the alternative numerator.\n"
            )
        )  

        denominator_formula: str = Field(
            description=(
                "Provide only the denominator part of the formula.\n"
                "- If no denominator exists, return '1'.\n"
                f"If previous_formula : {previous_formula}, then provide the alternative denominator.\n"
            )
        )  
        
        keywords_used: str = Field(
            description=(
        "Extract only the variables/terms that actually appear inside the formula expression.\n"
        "- Do NOT include the user query term itself (e.g., if query is 'FCFF', do not include 'FCFF').\n"
        "- Do NOT include explanatory words.\n"
        "- Return only the unique keywords exactly as they appear in the formula."
    )
)
    
    result = { 'user_query' : user_query }
    json_model = AzureChatOpenAI(
        model="gpt-4o",
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_VERSION"),
        max_tokens=1000,
        temperature=0
    ).with_structured_output(GetFormula)
    
    json_model_output = json_model.invoke(f"User Query : {user_query}")
    
    result["formula"] = json_model_output.formula
    result["numerator_formula"] = json_model_output.numerator_formula
    result["denominator_formula"] = json_model_output.denominator_formula
    result["keywords_used"] = json_model_output.keywords_used

    print(result)
    logging.info(f"Resulted Formula : {result}")
    
    return result



result_json = create_formula("adjusted present value")

# result_json = {'user_query': 'FCFF', 'formula': '( EBIT + 1 ) / Capital Expenditures', 'numerator_formula': 'EBIT * (1 - Tax Rate) + Depreciation - Change in Working Capital - Capital Expenditures', 'denominator_formula': '1', 'keywords_used': 'EBIT, Tax Rate, Depreciation, Change in Working Capital, Capital Expenditures'}
# print("Final Result:", evaluate_formula(result_json))

    

def category_mapping(user_query):
    class CategoryItem(BaseModel):
        sub_query: str = Field(
            description="The specific portion of the user query that refers to a time period or financial metric."
        )
        category: str = Field(
            description=(
                "The category assigned to this sub_query:\n"
                "- category_1: Static period (e.g., 'FY 2025', 'Sept 2022')\n"
                "- category_2: Latest/equivalent period (e.g., 'latest sales', 'last 3 quarters')\n"
                "- category_3: Range or comparative period (e.g., '2015 to 2018', 'highest quarter in FY 2024')\n"
                "- category_4: No period mentioned"
            )
        )

    class CategoryMapping(BaseModel):
        categories: list[CategoryItem] = Field(
            description="List of query parts with their respective categories."
        )

    result = {"user_query": user_query}

    json_model = AzureChatOpenAI(
        model="gpt-4o",
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_VERSION"),
        max_tokens=1000,
        temperature=0
    ).with_structured_output(CategoryMapping)

    json_model_output = json_model.invoke(f"User Query : {user_query}")

    result["categories"] = [c.model_dump() for c in json_model_output.categories]

    print(result)
    logging.info(f"Resulted Categories : {result}")

    return result


# category_mapping("what is the net revenue of fy24 and net profit from 2015 to 2018")
# category_mapping("what is market cap?")
# category_mapping("show me net profit for 2024")
# category_mapping("give me assets of 3 quarters")
# category_mapping("tell me the recent market cap")
# category_mapping("Give me promoter shareholding for FY 2022, compare it with FY 2024, and also show the latest available figure.")

