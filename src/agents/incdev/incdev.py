import json
import os
import re

from jinja2 import Environment, BaseLoader
from pathlib import Path
from src.config import Config
from src.llm import LLM
from src.agents.feature import Feature
from src.utils import shorten_path
from src.utils import read_Sysdesign
from src.project import ProjectManager

PROMPT = open("src/agents/incdev/prompt.jinja2").read().strip()


class Incdev:
    def __init__(self, base_model: str, search_engine: str):
        self.llm = LLM(model_id=base_model)
        config = Config()
        self.readsysdesign = read_Sysdesign
        self.project_manager = ProjectManager()
        self.project_dir = config.get_projects_dir()
        self.feature = Feature(base_model=base_model, search_engine=search_engine)

    def render(self, conversation: list, search_results: dict | dict[str, str],
               plans: str, file_code: str, file_name: str, selectedfiles: list[str], filenames: list[str],
               system_os: str) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(conversation=conversation, search_results=search_results, plans=plans,
                               file_code=file_code, file_name=file_name, selectedfiles=selectedfiles,
                               filenames=filenames, system_os=system_os)

    def validate_response(self, response: str):
        response = response.strip().replace("```json", "```")

        if response.startswith("```") and response.endswith("```"):
            response = response[3:-3].strip()

        try:
            response = json.loads(response)
        except Exception as _:
            return False

        for item in response:
            if "function" not in item or "args" not in item or "reply" not in item:
                return False

        return response

    def extractGitDiffInfoFromResponse(self, response) -> tuple | bool:
        # Initialize variables
        #global score
        gitdiff = []
        # summary = ''
        score = 0

        # Replace '~~~' at the beginning and end of the response
        if response.startswith("~~~"):
            response = response.replace("~~~", "", 1)
        if response.endswith("~~~"):
            response = response[::-1].replace("~~~"[::-1], "", 1)[::-1]

        response = response.strip()

        #if "~~~" in response:
         #   return False

        # Check if 'Gitdiff:', 'Summary:', and 'Score:' are in the response
        if 'Gitdiff:' not in response or 'Summary:' not in response or 'Score:' not in response:
            return False

        # Extract the Git diff block
        gitdiffMatch = response.split('Gitdiff:')[1].split('Summary:')[0].strip()
        gitdiffLines = gitdiffMatch.split('\n')

        gitdiff = []
        i = 0

        # Process the Git diff lines to extract changes
        while i < len(gitdiffLines):
            line = gitdiffLines[i].strip()

            if line.startswith('-'):
                oldLines = [line]
                newLines = []
                i += 1

                # Collect all contiguous '-' lines
                while i < len(gitdiffLines) and gitdiffLines[i].strip().startswith('-'):
                    oldLines.append(gitdiffLines[i].strip())
                    i += 1

                # Collect all contiguous '+' lines
                while i < len(gitdiffLines) and gitdiffLines[i].strip().startswith('+'):
                    newLines.append(gitdiffLines[i].strip())
                    i += 1

                gitdiff.append({'old': oldLines, 'new': newLines})

            elif line.startswith('+'):
                newLines = [line]
                oldLines = []
                i += 1

                # Collect all contiguous '+' lines
                while i < len(gitdiffLines) and gitdiffLines[i].strip().startswith('+'):
                    newLines.append(gitdiffLines[i].strip())
                    i += 1

                # Collect all contiguous '-' lines
                while i < len(gitdiffLines) and gitdiffLines[i].strip().startswith('-'):
                    oldLines.append(gitdiffLines[i].strip())
                    i += 1

                gitdiff.append({'old': oldLines, 'new': newLines})

            else:
                i += 1

        # Extract the Summary
        summary = response.split('Summary:')[1].split('Score:')[0].strip()

        # Extract the Score
        # score_str = response.split('Score:')[1].strip()
        pattern = r'Score:\s*(\d+)\s*:?'

        # Use regex to find the score
        match = re.search(pattern, response)

        if match:
            score_str = match.group(1)  # Get the score as a string
            score = int(score_str)  # Convert score to integer



        # Return the extracted values as a tuple
        return gitdiff, summary, score

    def execute(self, conversation: list, search_results: dict | dict[str, str], plans: str, project_name: str,
                system_os: str):
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
        filenames2 = list(dict.fromkeys(filenames))
        for file_name in filenames2:
            # Construct the full project file path based on the filename
            file_path = os.path.join(self.project_dir, project_name, file_name)
            file_pathnorm = os.path.normpath(file_path)
            # Remove any duplicate path separators

            # Check if the file exists
            if not os.path.isfile(file_pathnorm):
                print(f"File not found at: {file_name}. Creating it...")
                tempfiles = "<b>Creating...</b>:"+file_name
                self.project_manager.add_message_from_devika(project_name, tempfiles)
                #file_path1 = re.sub(r'\\+', '/', file_path)
                #file_path2 = shorten_path(file_path1)
                # Create the directory structure if it doesn't exist
                os.makedirs(os.path.dirname(file_pathnorm), exist_ok=True)
                with open(file_pathnorm, 'w', encoding="utf-8") as file:
                    file.write("")  # You can write some initial content here if needed

            # Read the file content and store it in file_code
            try:
                with open(file_pathnorm, 'r') as file:
                    file_code = file.read()
            except FileNotFoundError:
                print(f"File not found at: {file_pathnorm}")
                continue
            except Exception as e:
                print(f"Error reading file {file_name}: {e}")
                continue

            print(file_pathnorm)

            score = 1
            if score != 0:
                ext = Path(file_name).suffix.lower()
                if '.' not in file_name or ext in ['.jpg', '.png', '.jpeg', '.gif', '.bmp', '.tiff', '.placeholder',
                                                   '.ico', '.md', '.json','.svg','.txt']:
                    continue
                rendered_prompt = self.render(conversation, search_results, plans, file_code, file_name, [], filenames2,
                                              system_os)
                response = self.llm.inference(rendered_prompt, project_name)
                valide_response = self.extractGitDiffInfoFromResponse(response)
                if valide_response:
                    gitdiff, summary, score = self.extractGitDiffInfoFromResponse(response)
                    print(" score inside while ")
                    print(score)
                    print("gitdiff inside while ")
                    print("                          ")
                    print(gitdiff)
                    print("summary inside while")
                    print(summary)
                    print("                     ")
                    if score == 0:
                        continue
                    if not gitdiff:
                        continue
                    elif score != 0 and gitdiff:
                        print(score)
                        ext = Path(file_name).suffix.lower()
                        if '.' not in file_name or ext in ['.jpg', '.png', '.jpeg', '.gif','.tiff', '.bmp', '.placeholder', '.ico', '.md', '.json']:
                            continue
                        code = self.feature.execute(file_code, file_name, gitdiff, plans, filenames2,
                                                    summary, project_name, system_os)
                        print("\nfeature code :: ", code, "\n")
                        self.feature.save_code_to_project(code, project_name)
                    else:
                        # If score is not 10, the loop will continue with the same file_name
                        print(f"Score for {file_name} is {score}, retrying...")

    def execute1(self, conversation: list, selectedfiles: list[str], search_results: dict | dict[str, str], plans: str,
                 project_name: str,
                 system_os: str):

        filenames = self.readsysdesign(self.project_dir, project_name)

        print("inside incdev testing ")
        print(selectedfiles)
        for file_name in filenames:
            file_path = os.path.join(self.project_dir, project_name, file_name)
            if not os.path.isfile(file_path):
                selectedfiles.append(file_name)
        # remove duplicate in selectedfiles
        selectedfiles1 = list(dict.fromkeys(selectedfiles))
        for file_name in selectedfiles1:
            # Construct the full project file path based on the filename
            file_path = os.path.join(self.project_dir, project_name, file_name)
            # Remove any duplicate path separators
            file_pathnorm = os.path.normpath(file_path)

            # Check if the file exists
            if not os.path.isfile(file_pathnorm):
                print(f"File not found at: {file_pathnorm}. Creating it...")
                tempfiles = "<b>Creating...</b>:"+file_name
                self.project_manager.add_message_from_devika(project_name, tempfiles)
                #file_path1 = re.sub(r'\\+', '/', file_path)
                #file_path2 = shorten_path(file_path1)
                # Create the directory structure if it doesn't exist
                os.makedirs(os.path.dirname(file_pathnorm), exist_ok=True)
                with open(file_pathnorm, 'w', encoding="utf-8") as file:
                    file.write("")  # You can write some initial content here if needed

            # Read the file content and store it in file_code
            try:
                with open(file_pathnorm, 'r') as file:
                    file_code = file.read()
            except FileNotFoundError:
                print(f"File not found at: {file_pathnorm}")
                continue
            except Exception as e:
                print(f"Error reading file {file_name}: {e}")
                continue

            print(file_pathnorm)

            score = 1
            if score != 0:
                ext = Path(file_name).suffix.lower()
                if '.' not in file_name or ext in ['.jpg', '.png', '.jpeg', '.gif', '.bmp', '.tiff', '.placeholder',
                                                   '.ico', '.md', '.json','.svg','.txt']:
                    continue
                rendered_prompt = self.render(conversation, search_results, plans, file_code, file_name, selectedfiles1,
                                              filenames,
                                              system_os)
                response = self.llm.inference(rendered_prompt, project_name)
                valide_response = self.extractGitDiffInfoFromResponse(response)
                if valide_response:
                    gitdiff, summary, score = self.extractGitDiffInfoFromResponse(response)
                    print(" score inside while ")
                    print(score)
                    print("gitdiff inside while ")
                    print("                          ")
                    print(gitdiff)
                    print("summary inside while")
                    print(summary)
                    print("                     ")
                    if not gitdiff or score == 0:
                        continue
                    elif score != 0 and gitdiff:
                        print(score)
                        ext = Path(file_name).suffix.lower()
                        if '.' not in file_name or ext in ['.jpg', '.png', '.jpeg', '.gif', '.bmp','.tiff', '.placeholder', '.ico', '.md', '.json']:
                            continue
                        code = self.feature.execute(file_code, file_name, gitdiff, plans, filenames,
                                                    summary, project_name, system_os)
                        print("\nfeature code :: ", code, "\n")
                        self.feature.save_code_to_project(code, project_name)
                    else:
                        # If score is not 10, the loop will continue with the same file_name
                        print(f"Score for {file_name} is {score}, retrying...")
