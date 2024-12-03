import json
import os
from datetime import datetime
from typing import Optional
from sqlmodel import Field, Session, SQLModel, create_engine
from src.socket_instance import emit_agent
from src.config import Config


class AgentStateModel(SQLModel, table=True):
    __tablename__ = "agent_state"

    id: Optional[int] = Field(default=None, primary_key=True)
    project: str
    state_stack_json: str


class AgentState:
    def __init__(self):
        config = Config()
        sqlite_path = config.get_sqlite_db()
        self.engine = create_engine(f"sqlite:///{sqlite_path}")
        SQLModel.metadata.create_all(self.engine)

    def new_state(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "internal_monologue": None,
            "browser_session": {
                "url": None,
                "screenshot": None
            },
            "terminal_session": {
                "command": None,
                "output": None,
                "title": None
            },
            "step": None,
            "message": None,
            "completed": False,
            "agent_is_active": True,
            "token_usage": 0,
            "timestamp": timestamp
        }

    def delete_state(self, project: str):
        with Session(self.engine) as session:
            agent_state = session.query(AgentStateModel).filter_by(project=project).first()

            if agent_state:
                session.delete(agent_state)
                session.commit()

    def add_to_current_state(self, project: str, state: dict):
        with Session(self.engine) as session:
            agent_state = session.query(AgentStateModel).filter_by(project=project).first()
            if agent_state:
                state_stack = json.loads(agent_state.state_stack_json)
                state_stack.append(state)
                agent_state.state_stack_json = json.dumps(state_stack)
                session.commit()
            else:
                state_stack = [state]
                agent_state = AgentStateModel(project=project, state_stack_json=json.dumps(state_stack))
                session.add(agent_state)
                session.commit()
            # if projects == selectedprojects:
            emit_agent("agent-state", state_stack)
            ######
    def get_current_state(self, project: str):
        with Session(self.engine) as session:
            agent_state = session.query(AgentStateModel).filter_by(project=project).first()
            if agent_state:
                return json.loads(agent_state.state_stack_json)
            return None

    def update_latest_state(self, project: str, state: dict):
        with Session(self.engine) as session:
            agent_state = session.query(AgentStateModel).filter_by(project=project).first()
            if agent_state:
                state_stack = json.loads(agent_state.state_stack_json)
                state_stack[-1] = state
                agent_state.state_stack_json = json.dumps(state_stack)
                session.commit()
            else:
                state_stack = [state]
                agent_state = AgentStateModel(project=project, state_stack_json=json.dumps(state_stack))
                session.add(agent_state)
                session.commit()
            emit_agent("agent-state", state_stack)

    def get_latest_state(self, project: str):
        if not project:
            # If no project is selected, return None immediately
            return None
        with Session(self.engine) as session:
            agent_state = session.query(AgentStateModel).filter_by(project=project).first()
            if agent_state:
                return json.loads(agent_state.state_stack_json)[-1]
            return None

    def set_agent_active(self, project: str, is_active: bool):
        with Session(self.engine) as session:
            agent_state = session.query(AgentStateModel).filter_by(project=project).first()
            if agent_state:
                state_stack = json.loads(agent_state.state_stack_json)
                state_stack[-1]["agent_is_active"] = is_active
                agent_state.state_stack_json = json.dumps(state_stack)
                session.commit()
            else:
                state_stack = [self.new_state()]
                state_stack[-1]["agent_is_active"] = is_active
                agent_state = AgentStateModel(project=project, state_stack_json=json.dumps(state_stack))
                session.add(agent_state)
                session.commit()
            emit_agent("agent-state", state_stack)

    def is_agent_active(self, project: str):
        with Session(self.engine) as session:
            agent_state = session.query(AgentStateModel).filter_by(project=project).first()
            if agent_state:
                return json.loads(agent_state.state_stack_json)[-1]["agent_is_active"]
            return None

    def set_agent_completed(self, project: str, is_completed: bool):
        with Session(self.engine) as session:
            agent_state = session.query(AgentStateModel).filter_by(project=project).first()
            if agent_state:
                state_stack = json.loads(agent_state.state_stack_json)
                state_stack[-1]["internal_monologue"] = "Agent has completed the task."
                state_stack[-1]["completed"] = is_completed
                agent_state.state_stack_json = json.dumps(state_stack)
                session.commit()
            else:
                state_stack = [self.new_state()]
                state_stack[-1]["completed"] = is_completed
                agent_state = AgentStateModel(project=project, state_stack_json=json.dumps(state_stack))
                session.add(agent_state)
                session.commit()
            emit_agent("agent-state", state_stack)

    def is_agent_completed(self, project: str):
        with Session(self.engine) as session:
            agent_state = session.query(AgentStateModel).filter_by(project=project).first()
            if agent_state:
                return json.loads(agent_state.state_stack_json)[-1]["completed"]
            return None

    def update_token_usage(self, project: str, token_usage: int):
        with Session(self.engine) as session:
            agent_state = session.query(AgentStateModel).filter_by(project=project).first()
            if agent_state:
                state_stack = json.loads(agent_state.state_stack_json)
                state_stack[-1]["token_usage"] += token_usage
                agent_state.state_stack_json = json.dumps(state_stack)
                session.commit()
            else:
                state_stack = [self.new_state()]
                state_stack[-1]["token_usage"] = token_usage
                agent_state = AgentStateModel(project=project, state_stack_json=json.dumps(state_stack))
                session.add(agent_state)
                session.commit()

    def get_latest_token_usage(self, project: str):
        with Session(self.engine) as session:
            agent_state = session.query(AgentStateModel).filter_by(project=project).first()
            if agent_state:
                return json.loads(agent_state.state_stack_json)[-1]["token_usage"]
            return 0

    def get_project_files1(self, project_name: str):
        if not project_name:
            return []

        project_directory = "-".join(project_name.split(" "))
        directory = os.path.join(os.getcwd(), 'data', 'projects', project_directory)

        directory2 = os.path.join(directory, 'systemdesign', 'systemdesign.txt')

        if not os.path.exists(directory2):
            return []

        files = []
        excluded_files = ['.placeholder', 'newFile.js', 'favicon.ico', 'README.md', '.gitignore','LICENSE']  # Add the files you want to exclude here
        excluded_dirs = ['.git', 'systemdesign', '.idea', '.venv',
                         'node_modules', 'build', 'coverage', 'venv', '__pycache__']  # Add the directories you want to exclude here

        for root, _, filenames in os.walk(directory):
            if any(excluded_dir in root for excluded_dir in excluded_dirs):
                continue

            for filename in filenames:
                if filename in excluded_files:
                    continue

                file_relative_path = os.path.relpath(root, directory)
                if file_relative_path == '.':
                    file_relative_path = ''

                file_path = os.path.join(file_relative_path, filename)
                files.append(file_path)

        with open(directory2, 'w') as f:
            for file_path in files:
                f.write(f"{file_path}\n")

        return files

    import os

    def add_placeholder_to_empty_folders(self, project_name: str):
        if not project_name:
            return

        project_directory = "-".join(project_name.split(" "))
        directory = os.path.join(os.getcwd(), 'data', 'projects', project_directory)

        if not os.path.exists(directory):
            return

        excluded_dirs = ['.git', 'systemdesign', '.idea', '.venv',
                         'node_modules', 'build', 'coverage']  # Add the directories you want to exclude here

        for root, dirs, _ in os.walk(directory):
            for excluded_dir in excluded_dirs:
                if excluded_dir in dirs:
                    dirs.remove(excluded_dir)  # Exclude specified directories
            if not dirs and not os.listdir(root):  # Check if directory is empty
                placeholder_file = os.path.join(root, '.placeholder')
                if not os.path.exists(placeholder_file):
                    with open(placeholder_file, 'w') as placeholder:
                        placeholder.write("This folder intentionally left empty.")



    def get_project_files(self, project_name: str):
        """
        Retrieve all project files excluding certain directories and files.

        Args:
            project_name (str): The name of the project.

        Returns:
            list: A list of dictionaries containing file paths and their content.
        """
        if not project_name:
            return []

        # Construct the project directory path
        project_directory = "-".join(project_name.split(" "))
        directory = os.path.join(os.getcwd(), 'data', 'projects', project_directory)


        if not os.path.exists(directory):
            return []

        files = []
        # Directories and files to exclude from the search
        excluded_dirs = ['.git', 'systemdesign', '.idea', '.venv', 'node_modules', 'build', 'coverage', 'venv', '__pycache__']
        excluded_files = ['LICENSE', '.gitignore', 'favicon.ico']
        binary_file_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico','.svg','.txt']

        def is_binary_file(file_path):
            """
            Check if a file is binary based on its extension.

            Args:
                file_path (str): The path to the file.

            Returns:
                bool: True if the file is binary, False otherwise.
            """
            _, ext = os.path.splitext(file_path)
            return ext.lower() in binary_file_extensions

        for root, _, filenames in os.walk(directory):
            # Skip any directories listed in excluded_dirs
            if any(excluded_dir in root for excluded_dir in excluded_dirs):
                continue

            for filename in filenames:
                # Skip any files listed in excluded_files
                if filename in excluded_files:
                    continue

                file_relative_path = os.path.relpath(root, directory)
                if file_relative_path == '.':
                    file_relative_path = ''
                file_path = os.path.join(file_relative_path, filename)

                try:
                    file_full_path = os.path.join(root, filename)
                    if is_binary_file(file_full_path):
                        files.append({
                            "file": file_path,
                            "code": ""  # Return empty content for binary files
                        })
                    else:
                        with open(file_full_path, 'r', encoding='utf-8', errors='ignore') as file:
                            files.append({
                                "file": file_path,
                                "code": file.read()
                            })
                except Exception as e:
                    print(f"Error reading file {filename} at {root}: {e}")

        return files
