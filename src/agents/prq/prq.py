from jinja2 import Environment, BaseLoader

from src.config import Config
from src.llm import LLM
from src.utils import read_Sysdesign

PROMPT = open("src/agents/prq/prompt.jinja2").read().strip()
PROMPT1 = open("src/agents/prq/prompt4selectedfiles.jinja2").read().strip()


class Prq:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)
        config = Config()
        self.project_dir = config.get_projects_dir()
        self.readsysdesign = read_Sysdesign

    def render(self, prompt: str, readsysdesign1: list[str]) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(prompt=prompt, readsysdesign1=readsysdesign1)

    def render1(self, prompt: str, selectedfiles: list[str], readsysdesign1: list[str]) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT1)
        return template.render(prompt=prompt, selectedfiles=selectedfiles, readsysdesign1=readsysdesign1)

    def validate_response(self, response: str) -> bool | str:
        #
        # Define the delimiter
        delimiter = "```"
        # Check for the presence of the delimiter in the response
        # if delimiter not in response:
        #    response = response.strip()
        # Extract the content within the delimiters
        # if delimiter in response:
        #    response = response.split(delimiter, 1)[1]
        #   response = response[:response.rfind(delimiter)]
        # Trim whitespace from the response
        #   response = response.strip()

        # Placeholder for additional validation logic
        # TODO: Implement specific validation conditions
        response = response.strip()
        # Return True if the response passes all validation checks
        return response

    def execute(self, prompt: str, project_name: str) -> str:
        readsysdesign1 = self.readsysdesign(self.project_dir, project_name)
        prompt1 = self.render(prompt, readsysdesign1)
        response = self.llm.inference(prompt1, project_name)
        validate_response = self.validate_response(response)
        while not validate_response:
            print("Invalid response from formatter the model, trying again...")
            return self.execute(prompt, project_name)
        return validate_response

    def execute1(self, prompt: str, selectedfiles: list[str], project_name: str) -> str:
        readsysdesign1 = self.readsysdesign(self.project_dir, project_name)
        prompt1 = self.render1(prompt, selectedfiles, readsysdesign1)
        response = self.llm.inference(prompt1, project_name)
        validate_response = self.validate_response(response)
        while not validate_response:
            print("Invalid response from formatter the model, trying again...")
            return self.execute1(prompt, selectedfiles, project_name)
        return validate_response
