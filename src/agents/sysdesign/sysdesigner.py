import json
import os
import re
from typing import List

from jinja2 import Environment, BaseLoader

from src.llm import LLM
from src.config import Config

PROMPT = open("src/agents/sysdesign/prompt.jinja2").read().strip()


class Sysdesigner:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)
        config = Config()
        self.project_dir = config.get_projects_dir()

    def render(self, prompt: str, productrq: str, filenames: list[str]) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(prompt=prompt, productrq=productrq, filenames=filenames)

    def validate_response1(self, response: str) -> str | list[str]:
        response = response.strip()

        if not (response.startswith("~~~") and response.endswith("~~~")):
            return ""

        response = response[3:-3].strip().split('\n')

        for item in response:
            if not item.startswith("File: `") or not item.endswith("`"):
                return ""

        return response

    def validate_response(self, response: str) -> bool | list[str]:
        response = response.strip()

        # Replace '~~~' at the beginning and end of the response
        if response.startswith("~~~"):
            response = response.replace("~~~", "", 1)
        if response.endswith("~~~"):
            response = response[::-1].replace("~~~"[::-1], "", 1)[::-1]

        response = response.strip()

        # Split the response by lines
        response_lines = response.split('\n')

        files = []
        for item in response_lines:
            # Use regex to match the various formats
            match = re.match(r"File:\s*`?([^`]+)`?\s*:", item)
            if match:
                files.append(match.group(1))
            else:
                return False

        return files

    def extract_files(self, response: str):
        files = re.findall(r"File: `([^`]+)`", response)
        return files

    def execute(self, prompt: str, productrq: str, project_name: str) -> bool | list[str]:

        sstemdesign = "systemdesign"
        sstemdesign_txt = "systemdesign.txt"
        systemdesign_path = os.path.join(self.project_dir, project_name, sstemdesign, sstemdesign_txt)
        # Create the file if it doesn't exist
        try:
            file_path2 = os.path.normpath(systemdesign_path)
            os.makedirs(os.path.dirname(file_path2), exist_ok=True)
            with open(file_path2, "a+") as file:
                pass  # Do nothing
        except Exception as e:
            print(f"An error occurred while creating {systemdesign_path}: {e}")
        # Initialize filenames list
        filenames = []

        # Read systemdesign.txt content line by line with error handling
        try:
            with open(systemdesign_path, "r") as file:
                file.seek(0)
                for line in file:
                    # Strip newline characters and any leading/trailing whitespace
                    cleaned_line = line.strip()
                    # Add non-empty lines to filenames list
                    if cleaned_line:
                        filenames.append(cleaned_line)
                # Check if the file was empty
                print(filenames)
                if not filenames:
                    print(f"{systemdesign_path} is empty.")

        except Exception as e:
            print(f"An error occurred while reading {systemdesign_path}: {e}")

        # if not filenames:
        #    print("No valid file names found in systemdesign.txt")
        #    return
        filenames3 = list(dict.fromkeys(filenames))
        rendered_prompt = self.render(prompt, productrq, filenames3)
        response = self.llm.inference(rendered_prompt, project_name)

        valid_response = self.validate_response(response)

        while not valid_response:
            print("Invalid response from sysdesigner the model , trying again...")
            return self.execute(prompt, productrq, project_name)
        sstemdesign = "systemdesign"
        sstemdesign_txt = "systemdesign.txt"

        project_design0 = os.path.join(self.project_dir, project_name, sstemdesign)
        if not os.path.exists(project_design0):
            os.makedirs(project_design0, exist_ok=True)
        project_design = os.path.join(project_design0, sstemdesign_txt)
        project_design1 = os.path.normpath(project_design)
        files = self.validate_response(response)
        # Open the file with both read and append permissions
        with open(project_design1, "a+") as file:
            file.seek(0)  # Move the file pointer to the beginning of the file
            existing_files = file.read().splitlines()

            # Traverse the sxstemdesign.txt line by line
            for file_name in files:
                # Replace forward slashes with backslashes in the file path
                #
                file_name = file_name.replace('/', '\\')
                formatted_name_path = os.path.normpath(file_name)

                # If file in files does not exist in sxstemdesign.txt, add it in a new line
                if formatted_name_path not in existing_files:
                    file.write(formatted_name_path + "\n")

        return valid_response
