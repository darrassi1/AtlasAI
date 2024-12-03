import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from src.config import Config

class Gemini:
    def __init__(self):
        self.config = Config()
        api_key = self.config.get_gemini_api_key()
        genai.configure(api_key=api_key)

    def inference(self, model_id: str, prompt: str) -> str:
        # Fetching inference settings
        temperature = self.config.get_temperature()
        # max_token = self.config.get_max_token()
        top_p = self.config.get_top_p()

        # Create a GenerationConfig object with the fetched settings
        gen_config = genai.GenerationConfig(temperature=temperature, top_p=top_p)

        # Create a GenerativeModel object with the model_id and the generation_config
        model = genai.GenerativeModel(model_id, generation_config=gen_config)

        # Set safety settings for the request
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            # You can adjust other categories as needed
        }

        response = model.generate_content(prompt.strip(), safety_settings=safety_settings)
        try:
            # Check if the response contains text
            return response.text
        except ValueError:
            # If the response doesn't contain text, check if the prompt was blocked
            print("Prompt feedback:", response.prompt_feedback)
            # Also check the finish reason to see if the response was blocked
            print("Finish reason:", response.candidates[0].finish_reason)
            # If the finish reason was SAFETY, the safety ratings have more details
            print("Safety ratings:", response.candidates[0].safety_ratings)
            # Handle the error or return an appropriate message
            return "Error: Unable to generate content Gemini API"

