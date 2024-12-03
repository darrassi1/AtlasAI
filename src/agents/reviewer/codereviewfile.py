import json
import os
import re
from typing import List, Dict, Union, Tuple
from pathlib import Path
from jinja2 import Environment, BaseLoader

from src.llm import LLM
from src.config import Config
from src.utils import shorten_path
from src.agents.patcher import Patcher
from src.agents.planner import Planner
from src.project import ProjectManager

PROMPT = open("src/agents/reviewer/prompt.jinja2").read().strip()
PROMPT1 = open("src/agents/reviewer/prompt1.jinja2").read().strip()


class Codereviewfile:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)
        config = Config()
        self.project_dir = config.get_projects_dir()
        self.shorten_path = shorten_path("")
        self.patcher = Patcher(base_model=base_model)
        self.planner = Planner(base_model=base_model)
        self.project_manager = ProjectManager()

    def render(self, conversation: list, file_path: str, file_code: str, filenames: list) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(conversation=conversation, file_path=file_path, file_code=file_code, filenames=filenames)

    def render1(self, prompt: str, file_path: str, file_code: str, filenames: list) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT1)
        return template.render(prompt=prompt, file_path=file_path, file_code=file_code, filenames=filenames)

    def validate_response(self, response: str) -> tuple[str, str]:
        """
        Validates a response string from the model, checking format, returning data if valid.

        Args:
            response (str): The model response string.

        Returns:
            Union[Dict[str, str], bool]: A dictionary containing 'Review' and 'Raison' if valid, False otherwise.
        """

        response = response.strip()  # Remove leading/trailing whitespace

        # Check for the presence of delimiters
        if "~~~" not in response:
            return False

        # Extract the content between delimiters (assuming single occurrence)
        try:
            content = response.split("~~~")[1].strip()

        except ValueError:
            # Delimiter not found or invalid format, return False
            return False

        # Handle empty content before parsing
        if not content:  # Check if content is empty
            return False  # Or return an empty dictionary: {}

        # Try parsing the content as JSON
        try:
            data = json.loads(content)
            print(data)

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return False

        # If parsing successful, check for 'Review' key
        if "Review" not in data:
            print("Missing 'Review' key in response data.")
            return False

        # Return data or empty string for empty 'Raison'
        return data["Review"], data["Raison"]

    def extract_review_and_reason(self, response: str) -> tuple[str, str]:
        if response.startswith("~~~") and response.endswith("~~~"):
            response = response[3:-3].strip()
        parts = response.split("Reason:")
        if len(parts) >= 2:
            review = parts[0].strip()
            reason = parts[1].strip()
        else:
            review = parts[0].strip()
            reason = ""  # or some default value
        return review, reason

    def extract_filenames(self, systemdesign_content: str) -> list:
        """
        Extracts file names from the content of systemdesign.txt, handling potential errors.

        Args:
            systemdesign_content: The content of systemdesign.txt.

        Returns:
            A list of extracted file names or an empty list if there's an error.
        """

        filenames = []
        lines = systemdesign_content.splitlines()

        for line in lines:
            if line.startswith("File: "):  # Assuming lines start with "File: "
                try:
                    filename = line[6:].strip()  # Extract filename after "File: "
                    filenames.append(filename)
                except Exception as e:
                    print(f"Error parsing filename from line: {line} - {e}")

        return filenames

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
                file_subpath = os.path.normpath(file['file'])
                createdfile = "<b>Creating New file...</b>:" + file_subpath
                self.project_manager.add_message_from_devika(project_name, createdfile)
                # Create the directory structure if it doesn't exist
            os.makedirs(os.path.dirname(file_path2), exist_ok=True)
            with open(file_path2, "w+", encoding="utf-8") as f:
                f.write(file["code"])

        return os.path.join(project_dir, project_name)

    def execute(self, conversation: list, project_name: str):
        responseagentreview = "<mark>Agent Code Review: </mark><br>" + conversation[-1]
        self.project_manager.add_message_from_user(project_name, responseagentreview)
        # Define the path to systemdesign.txt
        sstemdesign = "systemdesign"
        sstemdesign_txt = "systemdesign.txt"
        systemdesign_path = os.path.join(self.project_dir, project_name, sstemdesign, sstemdesign_txt)

        # Initialize filenames list
        filenames = []

        # Read systemdesign.txt content line by line with error handling
        try:
            with open(systemdesign_path, "r") as file:
                for line in file:
                    # Strip newline characters and any leading/trailing whitespace
                    clean_line = line.strip()
                    # Add non-empty lines to filenames list
                    if clean_line:
                        filenames.append(clean_line)
        except FileNotFoundError:
            print(f"systemdesign.txt not found at: {systemdesign_path}")
            return
        except Exception as e:
            print(f"Error reading systemdesign.txt: {e}")
            return

        if not filenames:
            print("No valid file names found in systemdesign.txt")
            return

        # plan = self.planner.execute(conversation[-1], project_name)
        # planner_response = self.planner.parse_response(plan)
        # plans = planner_response["plans"]

        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if '.' not in filename or ext in ['.jpg', '.png', '.jpeg', '.gif', '.bmp', '.tiff', '.placeholder',
                                               '.ico', '.md', '.json']:
                continue
            # Construct the full project file path based on the filename
            file_path = os.path.join(self.project_dir, project_name, filename)

            # Read the file content and store it in file_code
            try:
                with open(file_path, 'r') as file:
                    file_code = file.read()
            except FileNotFoundError:
                print(f"File not found at: {file_path}")
                continue
            except Exception as e:
                print(f"Error reading file {filename}: {e}")
                continue
            print(file_path)
            # Review the file content using the LLM
            prompt = self.render(conversation, file_path, file_code, filenames)
            response = self.llm.inference(prompt, project_name)
            # Handle the response from the LLM here
            # print(response)
            # Validate and process LLM response
            Review, Reason = self.extract_review_and_reason(response)
            # print(valid_response)
            print(Review)
            print(Reason)
            if "LBTM" in Review:
                # print("am here")
                # Review, Reason = valid_response
                if "LBTM" == "LBTM":
                    ext = Path(filename).suffix.lower()
                    if '.' not in filename or ext in ['.jpg', '.png', '.jpeg', '.tiff', '.gif', '.bmp', '.placeholder','.ico', '.md', '.json']:
                        continue
                    responsereview = "<b>file </b>:" + filename + "<br>" + "<b>Review</b>:LBTM" + "<br>" + "<b>Reason</b>:" + Reason
                    self.project_manager.add_message_from_devika(project_name, responsereview)
                    self.patcher.executefromreview(conversation, filename, file_code, Reason, project_name)

    def execute4selectedfile(self, prompt: str, selected_files: list[str], project_name: str):
        responseagentreview = "<mark>Agent Code Review: </mark><br>" + "User Asked:" + prompt
        self.project_manager.add_message_from_user(project_name, responseagentreview)
        # Define the path to systemdesign.txt
        # sstemdesign = "systemdesign"
        # sstemdesign_txt = "systemdesign.txt"
        # systemdesign_path = os.path.join(self.project_dir, project_name, sstemdesign, sstemdesign_txt)

        # Initialize filenames list
        filenames = selected_files

        # plan = self.planner.execute(conversation[-1], project_name)
        # planner_response = self.planner.parse_response(plan)
        # plans = planner_response["plans"]

        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if '.' not in filename or ext in ['.jpg', '.png', '.jpeg', '.gif', '.bmp', '.tiff', '.placeholder',
                                               '.ico', '.md', '.json']:
                continue
            # Construct the full project file path based on the filename
            file_path = os.path.join(self.project_dir, project_name, filename)
            file_path2 = os.path.normpath(file_path)
            # Read the file content and store it in file_code
            try:
                with open(file_path2, 'r') as file:
                    file_code = file.read()
            except FileNotFoundError:
                print(f"File not found at: {file_path2}")
                continue
            except Exception as e:
                print(f"Error reading file {filename}: {e}")
                continue
            print(file_path2)
            # Review the file content using the LLM
            promptinf = self.render1(prompt, filename, file_code, filenames)
            response = self.llm.inference(promptinf, project_name)
            # Handle the response from the LLM here
            # print(response)
            # Validate and process LLM response
            Review, Reason = self.extract_review_and_reason(response)
            # print(valid_response)
            print(Review)
            print(Reason)
            if "LBTM" in Review:
                # print("am here")
                # Review, Reason = valid_response
                if "LBTM" == "LBTM":
                    ext = Path(filename).suffix.lower()
                    if '.' not in filename or ext in ['.jpg', '.png', '.jpeg', '.tiff', '.gif', '.bmp', '.placeholder','.ico', '.md', '.json']:
                        continue
                    responsereview = "<b>file </b>:" + filename + "<br>" + "<b>Review</b>:LBTM" + "<br>" + "<b>Reason</b>:" + Reason
                    self.project_manager.add_message_from_devika(project_name, responsereview)
                    self.patcher.executefromreview1(prompt, filename, file_code, Reason, project_name)

    def executeofcoder(self, prompt: str, project_name: str):
        # Define the path to systemdesign.txt
        sstemdesign = "systemdesign"
        sstemdesign_txt = "systemdesign.txt"
        systemdesign_path = os.path.join(self.project_dir, project_name, sstemdesign, sstemdesign_txt)

        # Initialize filenames list
        filenames = []

        # Read systemdesign.txt content line by line with error handling
        try:
            with open(systemdesign_path, "r") as file:
                for line in file:
                    # Strip newline characters and any leading/trailing whitespace
                    clean_line = line.strip()
                    # Add non-empty lines to filenames list
                    if clean_line:
                        filenames.append(clean_line)
        except FileNotFoundError:
            print(f"systemdesign.txt not found at: {systemdesign_path}")
            return
        except Exception as e:
            print(f"Error reading systemdesign.txt: {e}")
            return

        if not filenames:
            print("No valid file names found in systemdesign.txt")
            return

        # plan = self.planner.execute(conversation[-1], project_name)
        # planner_response = self.planner.parse_response(plan)
        # plans = planner_response["plans"]

        for filename in filenames:
            # Construct the full project file path based on the filename
            file_path = os.path.join(self.project_dir, project_name, filename)

            # Read the file content and store it in file_code
            try:
                with open(file_path, 'r') as file:
                    file_code = file.read()
            except FileNotFoundError:
                print(f"File not found at: {file_path}")
                continue
            except Exception as e:
                print(f"Error reading file {filename}: {e}")
                continue
            print(file_path)
            # Review the file content using the LLM
            prompt2 = self.render1(prompt, file_path, file_code, filenames)
            response = self.llm.inference(prompt2, project_name)
            # Handle the response from the LLM here
            # print(response)
            # Validate and process LLM response
            Review, Reason = self.extract_review_and_reason(response)
            # print(valid_response)
            print(Review)
            print(Reason)
            if "LBTM" in Review:
                ext = Path(filename).suffix.lower()
                if '.' not in filename or ext in ['.jpg', '.png', '.jpeg', '.tiff', '.gif', '.bmp', '.placeholder', '.ico','.md', '.json']:
                    continue
                # print("am here")
                # Review, Reason = valid_response
                if "LBTM" == "LBTM":
                    code = self.patcher.executefromreview1(prompt, filename, file_code, Reason, project_name)
                    self.save_code_to_project(code, project_name)
