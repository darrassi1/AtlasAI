from jinja2 import Environment, BaseLoader

from src.llm import LLM

PROMPT = open("src/agents/formatter/prompt.jinja2").read().strip()


class Formatter:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)

    def render(self, code_snippet: str, query:str) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(code_snippet=code_snippet,query=query)

    def validate_response(self, response: str) -> bool | str:
        #
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

        # Placeholder for additional validation logic
        # TODO: Implement specific validation conditions

        # Return True if the response passes all validation checks
        return response

    def execute(self, code_snippet: str,query:str, project_name: str) -> str:
        code_prompt = self.render(code_snippet,query)
        response = self.llm.inference(code_prompt, project_name)
        validate_response = self.validate_response(response)
        while not validate_response:
            print("Invalid response from formatter the model, trying again...")
            return self.execute(code_snippet,query, project_name)
        return validate_response
