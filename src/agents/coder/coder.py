import os
import re
import time

from jinja2 import Environment, BaseLoader
from typing import List, Dict, Union
from src.project import ProjectManager
from src.config import Config
from src.llm import LLM
from src.state import AgentState
from src.logger import Logger
from src.socket_instance import emit_agent
from src.utils import shorten_path

PROMPT = open("src/agents/coder/prompt.jinja2", "r").read().strip()


class Coder:
    def __init__(self, base_model: str):
        config = Config()
        self.project_dir = config.get_projects_dir()
        self.logger = Logger()
        self.llm = LLM(model_id=base_model)
        self.project_manager = ProjectManager()

    def render(
            self, step_by_step_plan: str | dict, user_context: str, search_results: dict, file_name: str, filenames: list, system_os: str
    ) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(
            step_by_step_plan=step_by_step_plan,
            user_context=user_context,
            search_results=search_results,
            file_name=file_name,
            filenames=filenames,
            system_os=system_os
        )

    def validate_response(self, response: str) -> Union[List[Dict[str, str]], bool]:
        response = response.strip()

        # Replace '~~~' at the beginning and end of the response
        if response.startswith("~~~"):
            response = response.replace("~~~", "", 1)
        if response.endswith("~~~"):
            response = response[::-1].replace("~~~"[::-1], "", 1)[::-1]

        response = response.strip()

        #if "~~~" in response:
         #   return False

        result = []
        current_file = None
        current_code = []
        code_block = False

        for line in response.split("\n"):
            if line.startswith("File:"):
                if current_file and current_code:
                    result.append({"file": os.path.normpath(current_file), "code": "\n".join(current_code)})
                if "`" in line:
                    current_file = line.split("`")[1].strip()
                elif line.startswith("File:") and line.endswith(":") and "`" not in line:
                    current_file = line.split(":")[1].strip()
                else:
                    print("Error: Line does not contain a backtick (`).")
                    return False
                current_code = []
                code_block = False
            elif line.startswith("```"):
                code_block = not code_block
            else:
                current_code.append(line)

        if current_file and current_code:
            result.append({"file": os.path.normpath(current_file), "code": "\n".join(current_code)})

        return result

    def save_code_to_project(self, response: List[Dict[str, str]], project_name: str):
        project_name = project_name.lower().replace(" ", "-")
        project_dir = os.path.join(self.project_dir, project_name)

        # Check if the project directory already exists
        if not os.path.exists(project_dir):
            os.makedirs(project_dir, exist_ok=True)
        for file in response:
            # No need to redefine file_path for each iteration
            file_path = os.path.join(project_dir, file['file'])
            # Remove any duplicate path separators
            #file_path1 = re.sub(r'\\+', '/', file_path)
            #file_path2 = shorten_path(file_path1)
            file_path2 = os.path.normpath(file_path)
            if not os.path.isfile(file_path2):
                # file_subpath = os.path.normpath(file['file'])
                createdfile = "<b>Creating New file...</b>:" + file['file']
                self.project_manager.add_message_from_devika(project_name, createdfile)
                # Create the directory structure if it doesn't exist
            os.makedirs(os.path.dirname(file_path2), exist_ok=True)
            with open(file_path2, "w+", encoding="utf-8") as f:
                f.write(file["code"])

        return os.path.join(project_dir, project_name)

    def get_project_path(self, project_name: str):
        project_name = project_name.lower().replace(" ", "-")
        return f"{self.project_dir}/{project_name}"

    def response_to_markdown_prompt(self, response: List[Dict[str, str]]) -> str:
        response = "\n".join([f"File: `{file['file']}`:\n```\n{file['code']}\n```" for file in response])
        return f"~~~\n{response}\n~~~"

    def emulate_code_writing(self, code_set: list, project_name: str):
        files = []
        for current_file in code_set:
            file = current_file["file"]
            code = current_file["code"]
            current_state = AgentState().get_latest_state(project_name)
            new_state = AgentState().new_state()
            new_state["browser_session"] = current_state["browser_session"]  # keep the browser session
            new_state["internal_monologue"] = "Writing code..."
            new_state["terminal_session"]["title"] = f"Editing {file}"
            new_state["terminal_session"]["command"] = f"vim {file}"
            new_state["terminal_session"]["output"] = code
            files.append({
                "file": file,
                "code": code
            })
            AgentState().add_to_current_state(project_name, new_state)
            # time.sleep(1)
        ## if projects == selectedprojects:
        emit_agent("code", {
            "files": files,
            "from": "coder"
        })
        #####
    def execute(
            self,
            step_by_step_plan: str | dict,
            user_context: str,
            search_results: dict,
            project_name: str,
            file_name: str,
            filenames: list,
            system_os: str
    ) -> list[dict[str, str]] | bool:

        prompt = self.render(step_by_step_plan, user_context, search_results, file_name, filenames, system_os)
        response = self.llm.inference(prompt, project_name)

        valid_response = self.validate_response(response)

        while not valid_response:
            print("Invalid response from coder the model, trying again...")
            return self.execute(step_by_step_plan, user_context, search_results, project_name, file_name, filenames, system_os)

        print(valid_response)

        self.emulate_code_writing(valid_response, project_name)

        return valid_response
