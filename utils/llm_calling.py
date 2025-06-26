import ollama
import logging
import ast
from openai import AzureOpenAI
import os
from dotenv import load_dotenv
import json
import re
import logging
from typing import Dict, Any


load_dotenv()

def get_gemma_response(system_prompt, user_prompt):
    model_name = "gemma3:1b"
# Define the user input prompt

# Run the model and get a response

    response = ollama.chat(model=model_name, messages=[{"role": "system", "content": system_prompt},{
        "role" : "user", "content" : user_prompt
    }])
    
    response = response.message.content

# Print the response
    return parse_llm_output(response)


def parse_llm_output(gpt_response: str) -> Dict[str, Any]:
    """
    Extracts and parses the outermost JSON object from the GPT response.
    
    Args:
        gpt_response (str): The GPT response to be parsed.
    
    Returns:
        dict: The parsed outermost JSON object, or empty dictionary if parsing fails.
    """
    if not gpt_response or not isinstance(gpt_response, str):
        logging.warning("Empty or invalid input provided.")
        return {}
    
    cleaned_response = gpt_response.strip()
    
    # Strategy 1: Try parsing the entire response as JSON
    try:
        parsed = json.loads(cleaned_response)
        logging.info("GPT response parsed successfully as complete JSON.")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        logging.debug("Complete response is not valid JSON, attempting extraction.")
    
    # Strategy 2: Extract the outermost JSON object
    try:
        # Find the first opening brace
        start_index = cleaned_response.find("{")
        if start_index == -1:
            logging.error("No opening brace found in response.")
            return {}
        
        # Find the matching closing brace by counting braces
        brace_count = 0
        end_index = -1
        
        for i in range(start_index, len(cleaned_response)):
            if cleaned_response[i] == "{":
                brace_count += 1
            elif cleaned_response[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_index = i
                    break
        
        if end_index == -1:
            logging.error("No matching closing brace found.")
            return {}
        
        # Extract the outermost JSON object
        json_str = cleaned_response[start_index:end_index + 1]
        
        # Parse the extracted JSON
        parsed = json.loads(json_str)
        logging.info("Outermost JSON object extracted and parsed successfully.")
        return parsed if isinstance(parsed, dict) else {}
        
    except json.JSONDecodeError as e:
        logging.error("Failed to parse extracted JSON: %s", e)
        logging.debug("Extracted content: %s", json_str[:200] + "..." if len(json_str) > 200 else json_str)
    except Exception as e:
        logging.error("Unexpected error during JSON extraction: %s", e)
    
    # Strategy 3: Handle code blocks (```json...```)
    try:
        code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(code_block_pattern, cleaned_response, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            parsed = json.loads(json_str)
            logging.info("JSON extracted from code block successfully.")
            return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError as e:
        logging.debug("Code block JSON parsing failed: %s", e)
    except Exception as e:
        logging.debug("Code block extraction failed: %s", e)
    
    logging.error("All parsing strategies failed; returning empty dictionary.")
    return {}

# def parse_llm_output(gpt_response: str) -> dict:
#     """
#     Attempts to parse the provided GPT response as a list or dictionary.
#     If that fails, extracts the content between the first and last curly braces
#     and parses it using ast.literal_eval.

#     Args:
#         gpt_response (str): The GPT response to be parsed.

#     Returns:
#         dict: The parsed GPT response as a dictionary, or an empty dictionary if parsing fails.
#     """
#     try:
#         # Attempt to parse the entire response
#         parsed = ast.literal_eval(gpt_response)
#         logging.info("GPT response parsed successfully using ast.literal_eval.")
#         if isinstance(parsed, (dict, list)):
#             return parsed
#         else:
#             logging.warning("Parsed output is not a dict or list; attempting extraction.")
#     except Exception as e:
#         logging.warning("Initial parsing failed: %s", e)

#     # Fallback: extract content between the first and last curly braces
#     try:
#         start_index = gpt_response.find("{")
#         end_index = gpt_response.rfind("}")
#         if start_index != -1 and end_index != -1:
#             extracted_content = gpt_response[start_index:end_index + 1]
#             parsed = ast.literal_eval(extracted_content)
#             logging.info("Extracted content parsed successfully.")
#             return parsed
#     except Exception as inner_e:
#         logging.exception("Failed to parse extracted content: %s", inner_e)

#     logging.error("Failed to parse GPT output; returning empty dictionary.")
#     return {}


def call_openai(system_prompt:str,user_prompt:str, model="gpt-4o-mini", temperature=0, parse_json = False):
    client = AzureOpenAI(api_key=os.getenv("AZURE_OPENAI_API_KEY"),azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),api_version=os.getenv("AZURE_OPENAI_VERSION"))
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens= 16000
    )
        
    if parse_json:
        return parse_llm_output(response.choices[0].message.content)
        
    else:
        return response.choices[0].message.content
