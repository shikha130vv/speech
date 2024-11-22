from dotenv import load_dotenv
import json
import requests
from PIL import Image as PILImage
from openai import AzureOpenAI
import os

load_dotenv(override=True)

def gen_dalle_img(theme, persona):
    file_name = f"images/{theme}_{persona}.png"
    if os.path.exists(file_name):
        return file_name
    if theme == "loan":
        if persona == "persona1":
            dalle_prompt = "Create a fun small child like cartoon character representing loan agent"
        else:
            dalle_prompt = "Create a fun small child like cartoon character representing customer interested in taking a loan"
    else:
        if persona == "persona1":
            dalle_prompt = "Create a fun small child like cartoon character representing marketing agent for contoso retail"
        else:
            dalle_prompt = "Create a fun small child like cartoon character representing customer interested in shopping offer"

    dalle_key = os.getenv("DALLE_KEY")
    dalle_ep = os.getenv("DALLE_EP")
    dalle_client = AzureOpenAI(
        api_version="2024-02-01",
        azure_endpoint=dalle_ep,
        api_key=dalle_key
    )

    result = dalle_client.images.generate(
        model="Dalle3", # the name of your DALL-E 3 deployment
        prompt=dalle_prompt,
        n=1
    )

    image_url = json.loads(result.model_dump_json())['data'][0]['url']

    response = requests.get(image_url)
    img_pil = PILImage.open(io.BytesIO(response.content))

    img_pil.save(file_name)