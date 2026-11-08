import json
import os
from openai import OpenAI

class AIHelper:
    def __init__(self, config_path='config.json'):
        self.config = self._load_config(config_path)
        llm_config = self.config.get('llm', {})
        
        self.client = OpenAI(
            base_url=llm_config.get('baseUrl', 'http://localhost:11434/v1'),
            api_key=llm_config.get('apiKey', 'ollama')
        )
        self.model = llm_config.get('model', 'qwen3-coder-30b')

    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def chat(self, user_message, system_message=None, history=None, stream=False):
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        if history:
            messages.extend(history)
            
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=stream
            )
            
            if stream:
                return response # Returns the generator
            else:
                return response.choices[0].message.content
        except Exception as e:
            return f"Error communicating with AI: {str(e)}"

if __name__ == "__main__":
    # Simple test
    helper = AIHelper()
    print("Testing connection to", helper.model)
    response = helper.chat("Hello! Are you ready to help with file conversions?")
    print("Response:", response)
