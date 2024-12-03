import json

from jinja2 import Environment, BaseLoader

from src.llm import LLM

PROMPT = open("src/agents/svgmaker/prompt.jinja2").read().strip()


class Svgmaker:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)

    def render(self, prompt: str) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(prompt=prompt)

    def validate_response(self, response: str):


        response = response.strip().replace("```json", "```")

        if response.startswith("```") and response.endswith("```"):
            response = response[3:-3].strip()



        return response

    def execute(self, prompt: str, project_name: str) -> str:
        rendered_prompt = self.render(prompt)
        response = self.llm.inference(rendered_prompt, project_name)

        valid_response = self.validate_response(response)
        # print(valid_response)
        while not valid_response:
            print("Invalid response from the model, trying again...")
            return self.execute(prompt, project_name)

        return valid_response