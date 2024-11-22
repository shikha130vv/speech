from dotenv import load_dotenv
from openai import AzureOpenAI
import os

load_dotenv(override=True)


open_ai_endpoint = os.getenv("OPEN_AI_ENDPOINT")
open_ai_key = os.getenv("OPEN_AI_KEY")
open_ai_deployment_name = os.getenv("OPEN_AI_DEPLOYMENT_NAME")
api_version = "2024-02-15-preview"

def create_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=open_ai_key,  # key
        azure_endpoint=open_ai_endpoint,  # gpt4
        api_version=api_version,  # ver
    )
client = create_openai_client()

def get_summary(language, agent_msgs):
    if language == "English":
        summary_prompt = "Create summary of the given conversation"
    else:
        summary_prompt = "आप बातचीत का सारांश तैयार करें।"
    # Concatenating all conversation content
    user_content = ''
    for entry in agent_msgs[1:]:
        role = entry["role"]
        content = entry["content"].replace("'","")
        user_content += f"{role}:{content}\n "

    # Creating the user role entry with concatenated content
    user_role = {'role': 'user', 'content': user_content.strip()}

    # Creating the final array
    system_summary_role = {'role': 'system', 'content': summary_prompt}
    final_array = [system_summary_role, user_role]
    print(final_array)
    completion = client.chat.completions.create(
            model=open_ai_deployment_name,
            messages=final_array,
            temperature=0,
            max_tokens=200,
            top_p=0.95,
            frequency_penalty=0.5,
            presence_penalty=0.5,
            stream=False
        )
    return completion.choices[0].message.content