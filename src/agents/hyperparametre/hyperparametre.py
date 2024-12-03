import json

from jinja2 import Environment, BaseLoader

from src.llm import LLM

PROMPT = open("src/agents/hyperparametre/prompt.jinja2").read().strip()


class Hyperparametre:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)

    def render(self, temperature: float, max_token: float, top_p: float) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(temperature=temperature, max_token=max_token, top_p=top_p)

    def validate_response(self, response: str):
        response = response.strip().replace("```json", "```")

        if response.startswith("```") and response.endswith("```"):
            response = response[3:-3].strip()

        return response

    def execute(self, temperature: float, max_token: float, top_p: float, project_name: str) -> str:
        rendered_prompt = self.render(temperature, max_token, top_p)
        response = self.llm.inference(rendered_prompt, project_name)

        valid_response = self.validate_response(response)

        while not valid_response:
            print("Invalid response from the model hyperparametre, trying again...")
            return self.execute(temperature, max_token, top_p, project_name)

        return valid_response
