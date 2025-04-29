import ollama
import logging
import ast
from openai import AzureOpenAI
import os
from dotenv import load_dotenv

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

def parse_llm_output(gpt_response: str) -> dict:
    """
    Attempts to parse the provided GPT response as a list or dictionary.
    If that fails, extracts the content between the first and last curly braces
    and parses it using ast.literal_eval.

    Args:
        gpt_response (str): The GPT response to be parsed.

    Returns:
        dict: The parsed GPT response as a dictionary, or an empty dictionary if parsing fails.
    """
    try:
        # Attempt to parse the entire response
        parsed = ast.literal_eval(gpt_response)
        logging.info("GPT response parsed successfully using ast.literal_eval.")
        if isinstance(parsed, (dict, list)):
            return parsed
        else:
            logging.warning("Parsed output is not a dict or list; attempting extraction.")
    except Exception as e:
        logging.warning("Initial parsing failed: %s", e)

    # Fallback: extract content between the first and last curly braces
    try:
        start_index = gpt_response.find("{")
        end_index = gpt_response.rfind("}")
        if start_index != -1 and end_index != -1:
            extracted_content = gpt_response[start_index:end_index + 1]
            parsed = ast.literal_eval(extracted_content)
            logging.info("Extracted content parsed successfully.")
            return parsed
    except Exception as inner_e:
        logging.exception("Failed to parse extracted content: %s", inner_e)

    logging.error("Failed to parse GPT output; returning empty dictionary.")
    return {}

def call_openai(system_prompt:str,user_prompt:str, model="gpt-4o-mini", temperature=0):
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
    return response.choices[0].message.content
