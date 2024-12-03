from groq import Groq as _Groq
from src.config import Config


class Groq:
    def __init__(self):
        self.config = Config()
        api_key = self.config.get_groq_api_key()
        self.client = _Groq(api_key=api_key)

    def inference(self, model_id: str, prompt: str) -> str:
        temperature = self.config.get_temperature()
        # max_token = self.config.get_max_token()
        top_p = self.config.get_top_p()

        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt.strip(),
                }
            ],
            model=model_id,
            temperature=temperature,
            top_p=top_p
        )

        return chat_completion.choices[0].message.content
