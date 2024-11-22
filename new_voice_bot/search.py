import os
import requests
import urllib.parse

bing_key = os.getenv('VITE_BING_API_KEY')

def bing_web_search(query: str) -> str:
    base_url = 'https://api.bing.microsoft.com/v7.0/search'
    headers = {
        'Ocp-Apim-Subscription-Key': bing_key
    }
    
    params = {
        'q': urllib.parse.quote(query)
    }
    
    response = requests.get(base_url, headers=headers, params=params)
    response.raise_for_status()  # Ensure the request was successful
    
    query_result = response.json()
    
    result = "search results: "
    if "webPages" in query_result:
        pages = query_result["webPages"]["value"]
        for page in pages:
            result += f" title: {page['name']}, snippet: {page['snippet']}\n"
    
    print(result)
    return result
