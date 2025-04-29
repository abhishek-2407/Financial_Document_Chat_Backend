import logging
import os

from dotenv import load_dotenv


if len(logging.getLogger().handlers) > 0:
    logging.getLogger().setLevel(logging.INFO)
else:

    logging.basicConfig(level=logging.INFO)


def _set_env():
    load_dotenv()

    #Get and set azure openai credentials
    os.environ["AZURE_OPENAI_API_KEY"] = os.getenv("AZURE_OPENAI_API_KEY", "")
    os.environ["AZURE_OPENAI_ENDPOINT"] = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    os.environ["OPENAI_API_VERSION"] = os.getenv("AZURE_OPENAI_VERSION", "2024-05-13")
  
_set_env()


