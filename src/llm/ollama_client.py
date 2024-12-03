import ollama
from src.logger import Logger
from src.config import Config

log = Logger()


class Ollama:
    def __init__(self):
        self.config = Config()
        try:
            self.client = ollama.Client(self.config.get_ollama_api_endpoint())
            self.models = self.client.list()["models"]
            log.info("Ollama available")
        except Exception as e:
            self.client = None
            log.warning("Ollama not available: " + str(e))
            log.warning("Run Ollama server to use Ollama models; otherwise, use other models.")

    def inference(self, model_id: str, prompt: str) -> str:
        temperature = self.config.get_temperature()
        # max_token = self.config.get_max_token()
        top_p = self.config.get_top_p()

        response = self.client.generate(
            model=model_id,
            prompt=prompt.strip(),
            options={
                "temperature": temperature,
                # "max_tokens": max_token,
                "top_p": top_p
            }
        )
        return response['response']
