import os
import re
import time

from jinja2 import Environment, BaseLoader
from typing import List, Dict, Union
from src.socket_instance import emit_agent
from src.project import ProjectManager
from src.config import Config
from src.llm import LLM
from src.state import AgentState
from src.utils import shorten_path

PROMPT = open("src/agents/patcher/prompt.jinja2", "r").read().strip()
PROMPT1 = open("src/agents/patcher/prompt1.jinja2", "r").read().strip()

class Patcher:
    def __init__(self, base_model: str):
        config = Config()
        self.project_dir = config.get_projects_dir()
        self.shorten_path = shorten_path("")
        self.llm = LLM(model_id=base_model)
        self.project_manager = ProjectManager()

    def render(
            self,
            conversation: list,
            code_markdown: str,
            commands: list,
            error: str,
            system_os: str
    ) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(
            conversation=conversation,
            code_markdown=code_markdown,
            commands=commands,
            error=error,
            system_os=system_os
        )

    def renderfromreview(self, conversation: list, filename: str, file_code: str, reason: str, project_name: str) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(
            conversation=conversation,
            filename=filename,
            file_code=file_code,
            reason=reason,
            project_name=project_name
        )
    def renderfromreview1(self, prompt: str, filename: str, file_code: str, reason: str, project_name: str) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT1)
        return template.render(
            prompt=prompt,
            filename=filename,
            file_code=file_code,
            reason=reason,
            project_name=project_name
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
            # file_subpath = os.path.normpath(file)
            new_state = AgentState().new_state()
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
        emit_agent("code", {
            "files": files,
            "from": "patcher"
        })

    def executefromreview(
            self,
            conversation: list,
            filename: str,
            file_code: str,
            reason: str,
            project_name: str
    ) -> Union[List[Dict[str, str]], bool]:

        prompt = self.renderfromreview(conversation, filename, file_code, reason, project_name)
        response = self.llm.inference(prompt, project_name)

        valid_response = self.validate_response(response)

        while not valid_response:
            print("Invalid response from patcher model, trying again...")
            return self.executefromreview(conversation, filename, file_code, reason, project_name)

        self.emulate_code_writing(valid_response, project_name)
        self.save_code_to_project(valid_response, project_name)

        return valid_response

    def executefromreview1(
            self,
            prompt: str,
            filename: str,
            file_code: str,
            reason: str,
            project_name: str
    ) -> Union[List[Dict[str, str]], bool]:

        prompt2 = self.renderfromreview1(prompt, filename, file_code, reason, project_name)
        response = self.llm.inference(prompt2, project_name)

        valid_response = self.validate_response(response)

        while not valid_response:
            print("Invalid response from patcher model, trying again...")
            return self.executefromreview1(prompt, filename, file_code, reason, project_name)

        self.emulate_code_writing(valid_response, project_name)

        return valid_response

    def execute(self, conversation: List, code_markdown: str, commands: List, error: str, system_os: str,
                project_name: str) -> Union[List[Dict[str, str]], bool]:
        prompt = self.render(conversation, code_markdown, commands, error, system_os)
        response = self.llm.inference(prompt, project_name)

        valid_response = self.validate_response(response)

        while not valid_response:
            print("Invalid response from the model, trying again...")
            return self.execute(conversation, code_markdown, commands, error, system_os, project_name)

        self.emulate_code_writing(valid_response, project_name)

        return valid_response
