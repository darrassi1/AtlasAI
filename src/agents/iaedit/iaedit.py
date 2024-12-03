import json

from jinja2 import Environment, BaseLoader

from src.config import Config
from src.llm import LLM

PROMPT = open("src/agents/iaedit/prompt.jinja2", "r").read().strip()
PROMPT1 = open("src/agents/iaedit/autocompletion.jinja2", "r").read().strip()


class Iaedit:
    def __init__(self, base_model: str):
        config = Config()
        self.project_dir = config.get_projects_dir()

        self.llm = LLM(model_id=base_model)

    def render(
            self, prompt: str, code: str
    ) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(
            prompt=prompt,
            code=code
        )

    def render1(
            self, language: str, code: str
    ) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT1)
        return template.render(
            language=language,
            code=code
        )

    def validate_response(self, response: str):
        response = response.strip().replace("```json", "```")
        response = response.strip().replace("```python", "```")
        if "```" not in response:
            return False
        response = response.split("```", 1)[1]
        response = response[:response.rfind("```")]
        # Remove extra backticks at the start or end
        response = response.strip("`")

        return response

    def validate_response1(self, response: str):
        if not response:
            print("Empty response")
            return False
        # Define the delimiter
        delimiter = "```"
        # Check for the presence of the delimiter in the response
        if delimiter not in response:
            response = response.strip()
        # Extract the content within the delimiters
        if delimiter in response:
            response = response.split(delimiter, 1)[1]
            response = response[:response.rfind(delimiter)]
            # Trim whitespace from the response
            response = response.strip()

        try:
            suggestions = json.loads(response)
            if not isinstance(suggestions, list):
                print("Response is not a list")
                return False
            for suggestion in suggestions:
                if not isinstance(suggestion, dict) or 'text' not in suggestion:
                    print("Invalid suggestion format")
                    return False
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return False
        except Exception as e:
            print(f"Error validating response: {e}")
            return False

        return suggestions
    def rectify_code_function(self, prompt: str, code: str, project_name: str) -> str:
        prompt1 = self.render(prompt, code)
        response = self.llm.inference(prompt1, project_name)
        valid_response = self.validate_response(response)

        while not valid_response:
            print("Invalid response from the model iaedit, trying again...")
            return self.rectify_code_function(prompt, code, project_name)

        return valid_response

    def autocompletion(self, language: str, code: str, project_name: str) -> list[str]:
        prompt1 = self.render1(language, code)
        response = self.llm.inference(prompt1, project_name)
        valid_response = self.validate_response1(response)
        print("valide response from autopilot")
        print("                                ")
        print("                                ")
        print("                                ")
        print(valid_response)
        print("                                ")
        print("                                ")
        print("                                ")
        while not valid_response:
            print("Invalid response from the model iaedit, trying again...")
            return self.autocompletion(language, code, project_name)

        return valid_response

    def execute(self, conversation: list, code_markdown: str, project_name: str) -> str:
        prompt = self.render(conversation, code_markdown)
        response = self.llm.inference(prompt, project_name)

        valid_response = self.validate_response(response)

        while not valid_response:
            print("Invalid response from the model, trying again...")
            return self.execute(conversation, code_markdown, project_name)

        return valid_response
