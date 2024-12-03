from typing import List, Union, Dict

from src.agents.agent_template import AgentTemplate
from src.browser.search import BingSearch
from src.llm import LLM
from src.logger import Logger

logger = Logger()


class Researcher(AgentTemplate):
    def __init__(self, base_model: str):
        self.bing_search = BingSearch()
        self.llm = LLM(model_id=base_model)

        super().__init__()

    def __validate_response(self, response: dict) -> dict:
        if len(response["queries"]) > 3:
            logger.warning(
                "The research agent asked for too many queries, only keeping the first 3"
            )
            response["queries"] = response["queries"][:3]

        return response

    def execute(
        self, step_by_step_plan: str, contextual_keywords: List[str], project_name: str
    ) -> dict | bool:
        contextual_keywords_str = ", ".join(
            map(lambda k: k.capitalize(), contextual_keywords)
        )
        prompt = self.render(
            step_by_step_plan=step_by_step_plan,
            contextual_keywords=contextual_keywords_str,
        )

        response = self.llm.inference(prompt, project_name)

        # Parse the response using REGEX
        parsed_response = self.parse_answer(response)

        try:
            # Rafine and validate the response
            valid_response = self.__validate_response(parsed_response)
        except Exception as e:
            print(f"Error during validation: {e}")
            valid_response = False

        while not valid_response:
            print("Invalid response from the model, trying again...")
            return self.execute(step_by_step_plan, contextual_keywords, project_name)

        return valid_response
