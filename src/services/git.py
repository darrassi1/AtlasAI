import json
import os

import git as GitPython

from jinja2 import Environment, BaseLoader
from src.llm import LLM

PROMPT = open("src/services/prompt.jinja2").read().strip()
PROMPT1 = open("src/services/prompt1.jinja2").read().strip()


class Git:

    def __init__(self, path, base_model: str):
        self.llm = LLM(model_id=base_model)
        try:
            self.repo = GitPython.Repo(path)
        except GitPython.exc.InvalidGitRepositoryError:
            self.repo = self.initialize(path)

    def render(
            self, conversation: str, code_markdown: str, code_diff: str
    ) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(
            conversation=conversation,
            code_markdown=code_markdown,
            code_diff=code_diff
        )

    def render1(self, conversation: str) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT1)
        return template.render(
            conversation=conversation
        )

    def validate_response(self, response: str):
        response = response.strip().replace("```json", "```")

        try:
            response = response.split("```")[1].split("```")[0]
            response = json.loads(response)
        except Exception as _:
            return False

        if "commit_message" not in response:
            return False
        else:
            return response["commit_message"]

    def validate_response1(self, response: str) -> str | bool:
        response = response.strip().replace("```json", "```")

        try:
            response = response.split("```")[1].split("```")[0]
            response = json.loads(response)
        except Exception as _:
            return False

        if "url" not in response:
            return False
        else:
            # Extract the URL from the response
            url = response["url"]
            # Validate the URL
            if url.startswith("http://") or url.startswith("https://"):
                return url
            else:
                print("Invalid URL")
                return False

    def initialize(self, path):
        return GitPython.Repo.init(path)

    def commit(self, message):
        self.repo.index.add("*")
        self.repo.index.commit(message)

    def generate_commit_message(self, project_name, conversation, code_markdown):
        # Get the code diff
        try:
            code_diff = self.repo.git.diff()
        except GitPython.exc.GitCommandError:
            code_diff = ""

        prompt = self.render(conversation, code_markdown, code_diff)
        response = self.llm.inference(prompt, project_name)
        print(response)

        valid_response = self.validate_response(response)

        while not valid_response:
            print("Invalid response from the model, trying again...")
            return self.generate_commit_message(project_name, conversation, code_markdown)

        return valid_response

    def responseurl(self, project_name, conversation) -> str:
        prompt1 = self.render1(conversation)
        response = self.llm.inference(prompt1, project_name)


        valid_response = self.validate_response1(response)

        return valid_response

    def reset_to_previous_commit(self):
        try:
            self.repo.git.reset("--hard", "HEAD^")
            print("Resetting to previous commit was successful.")
            return True
        except GitPython.exc.GitCommandError as e:
            print(f"Error resetting to previous commit: {e}")
            return False

    def clone(self, path, project_name, conversation):
        url = self.responseurl(project_name, conversation)
        print(url)
        if url:
            # Extract the repository name from the URL
            repo_name = url.split('/')[-1]
            # Append the repository name to the path
            full_path = os.path.join(path, repo_name)
            # Create the directory if it doesn't exist
            os.makedirs(full_path, exist_ok=True)
            try:
                return GitPython.Repo.clone_from(url, full_path)
            except Exception as e:
                print(f"An error occurred while cloning the repository: {e}")
                return None
        else:
            print("Invalid URL")
            return None

    def get_branches(self):
        return self.repo.branches

    def get_commits(self, branch):
        return self.repo.iter_commits(branch)

    def get_commit(self, commit):
        return self.repo.commit(commit)

    def get_file(self, commit, file):
        return self.repo.git.show(f'{commit}:{file}')
