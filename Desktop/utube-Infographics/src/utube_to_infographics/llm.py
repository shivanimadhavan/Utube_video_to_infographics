# src/llm.py

import os
from langchain_openai import AzureChatOpenAI
import os
import json
from dotenv import load_dotenv
load_dotenv()


def get_llm():
    deployment_json = os.environ.get("AZURE_DEPLOYMENT_DEFAULTS")
    if deployment_json:
       dd = json.loads(deployment_json)
       deployment = dd.get("deployment_names", {}).get("gpt-4.1", "gpt-4.1")
    else:
       deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]       

    return AzureChatOpenAI(
        azure_deployment=deployment,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        temperature=0.2
    )