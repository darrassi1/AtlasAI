from jinja2 import Environment, BaseLoader

from src.llm import LLM
from src.agents.sysdesign import Sysdesigner
from src.utils import read_Sysdesign
from src.config import Config

PROMPT = open("src/agents/planner/prompt.jinja2").read().strip()
PROMPT1 = open("src/agents/planner/promptselectedfiles.jinja2").read().strip()


class Planner:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)
        self.sysdesign = Sysdesigner(base_model=base_model)
        self.readsysdesign = read_Sysdesign
        config = Config()
        self.project_dir = config.get_projects_dir()

    def render(self, prompt: str, productrq: str, design: bool | list[str]) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(prompt=prompt, productrq=productrq, design=design)

    def render1(self, prompt: str, productrq: str, design: bool | list[str], selectedfiles: list[str]) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT1)
        return template.render(prompt=prompt, productrq=productrq, design=design, selectedfiles=selectedfiles)

    def validate_response(self, response: str) -> bool | str:
        response = response.strip()

        # Replace '~~~' at the beginning and end of the response
        if response.startswith("```"):
            response = response.replace("```", "", 1)
        if response.endswith("```"):
            response = response[::-1].replace("```"[::-1], "", 1)[::-1]

        response = response.strip()

        # Placeholder for additional validation logic
        # TODO: Implement specific validation conditions

        # Return the cleaned response if it passes all validation checks
        return response

    def parse_response(self, response: str):
        result = {
            "project": "",
            "reply": "",
            "focus": "",
            "plans": {},
            "summary": ""
        }

        current_section = None
        current_step = None

        for line in response.split("\n"):
            line = line.strip()

            if line.startswith("Project Name:"):
                current_section = "project"
                result["project"] = line.split(":", 1)[1].strip()
            elif line.startswith("Your Reply to the Human Prompter:"):
                current_section = "reply"
                result["reply"] = line.split(":", 1)[1].strip()
            elif line.startswith("Current Focus:"):
                current_section = "focus"
                result["focus"] = line.split(":", 1)[1].strip()
            elif line.startswith("Plan:"):
                current_section = "plans"
            elif line.startswith("Summary:"):
                current_section = "summary"
                result["summary"] = line.split(":", 1)[1].strip()
            elif current_section == "reply":
                if line:
                    result["reply"] += " " + line
            elif current_section == "focus":
                if line:
                    result["focus"] += " " + line
            elif current_section == "plans":
                if line.startswith("- [ ] Step"):
                    try:
                        current_step = float(line.split(":")[0].strip().split(" ")[-1])
                        result["plans"][current_step] = line.split(":", 1)[1].strip()
                    except (ValueError, IndexError):
                        print(f"Error: Malformed plan step line: {line}")
                        current_step = None
                elif current_step is not None:
                    result["plans"][current_step] += " " + line
            elif current_section == "summary":
                if line:
                    result["summary"] += " " + line.replace("```", "")

        # Final strip to clean up any leading/trailing whitespace
        result["project"] = result["project"].strip()
        result["reply"] = result["reply"].strip()
        result["focus"] = result["focus"].strip()
        result["summary"] = result["summary"].strip()

        return result

    def execute(self, prompt: str, productrq: str, project_name: str) -> str:
        design = self.sysdesign.execute(prompt, productrq, project_name)
        prompt2 = self.render(prompt, productrq, design)
        response = self.llm.inference(prompt2, project_name)
        validate_response = self.validate_response(response)

        while not validate_response:
            print("Invalid response from planner the model, trying again...")
            return self.execute(prompt, productrq, project_name)
        return validate_response

    def execute1(self, prompt: str, productrq: str, selectedfiles: list[str], project_name: str) -> str:
        #design = self.readsysdesign(self.project_dir, project_name)
        design = self.sysdesign.execute(prompt, productrq, project_name)
        prompt2 = self.render1(prompt, productrq, design, selectedfiles)
        response = self.llm.inference(prompt2, project_name)
        validate_response = self.validate_response(response)

        while not validate_response:
            print("Invalid response from planner the model, trying again...")
            return self.execute1(prompt, productrq,selectedfiles, project_name)
        return validate_response
