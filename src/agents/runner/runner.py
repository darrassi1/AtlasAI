import platform
import queue
import threading
import time
import json
import os
import subprocess

from google.api_core.exceptions import DeadlineExceeded
from jinja2 import Environment, BaseLoader
# Determine if running on Windows
is_windows = platform.system() == 'Windows'

if not is_windows:
    import pty
    import signal

from src.agents.patcher import Patcher
from src.llm import LLM
from src.logger import Logger
from src.socket_instance import emit_agent
from src.state import AgentState
from src.project import ProjectManager

PROMPT_PATH = "src/agents/runner/prompt.jinja2"
RERUNNER_PROMPT_PATH = "src/agents/runner/rerunner.jinja2"
# Store the process state
process_dict = {}
def load_prompt(path):
    with open(path, "r", encoding='utf8') as file:
        return file.read().strip()

PROMPT = load_prompt(PROMPT_PATH)
RERUNNER_PROMPT = load_prompt(RERUNNER_PROMPT_PATH)

class Runner:
    def __init__(self, base_model: str):
        self.base_model = base_model
        self.llm = LLM(model_id=base_model)
        self.env = Environment(loader=BaseLoader())
        self.logger = Logger()
        self.retry_limit = 5
        self.lock = threading.Lock()


    def render_template(self, template_str, **kwargs):
        template = self.env.from_string(template_str)
        return template.render(**kwargs)

    def render(self, conversation, code_markdown, system_os):
        return self.render_template(PROMPT, conversation=conversation, code_markdown=code_markdown, system_os=system_os)

    def render_rerunner(self, conversation, code_markdown, system_os, commands, error):
        return self.render_template(RERUNNER_PROMPT, conversation=conversation, code_markdown=code_markdown, system_os=system_os, commands=commands, error=error)

    def parse_response(self, response):
        response = response.strip().replace("json", "")
        if response.startswith("```") and response.endswith("```"):
            response = response[3:-3].strip()
            print(response)
            print("line 49 runner")
        return json.loads(response)

    def validate_response(self, response):
        try:
            parsed_response = self.parse_response(response)
            commands = parsed_response.get("commands", [])
            if commands:
                return commands
            else:
                return []
        except (json.JSONDecodeError, KeyError):
            return []

    def validate_rerunner_response(self, response):
        try:
            parsed_response = self.parse_response(response)
            return parsed_response if "action" in parsed_response and "response" in parsed_response else False
        except (json.JSONDecodeError, KeyError):
            return False
    def execute_subprocess(self, command, project_path, project_name,result_queue):
        try:
            def run_process():
                nonlocal command, project_path, project_name
                try:
                    if is_windows:
                        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=project_path, shell=True)
                    else:
                        master, slave = pty.openpty()
                        process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=project_path, shell=True, preexec_fn=os.setsid)
                        os.close(slave)

                    pid = process.pid

                    # Store process information
                    with self.lock:
                        process_dict[pid] = process

                    # Emit the process ID to the frontend
                    emit_agent("pid", {"command": command, "pid": pid})

                    output = ""

                    # Function to read and handle output
                    def read_output():
                        nonlocal output
                        if is_windows:
                            while True:
                                data = process.stdout.read(4096).decode('utf-8', errors='ignore')
                                if not data:
                                    break
                                output += data
                                monologue = f"running the command '{command}': {output}"
                                self.update_state(project_name, command, output, monologue=monologue)
                        else:
                            while True:
                                try:
                                    data = os.read(master, 4096).decode('utf-8', errors='ignore')
                                    if not data:
                                        break
                                    output += data
                                    monologue = f"running the command '{command}': {output}"
                                    self.update_state(project_name, command, output, monologue=monologue)
                                except OSError:
                                    break

                    output_thread = threading.Thread(target=read_output)
                    output_thread.start()

                    returncode = process.wait()

                    # output_thread.join() # Wait for the thread to finish will block main process

                    with self.lock:
                        del process_dict[pid]
                        tes = "killed"
                        emit_agent("pidkilled", {"command": tes, "pid": pid})

                    result_queue.put((output, False))
                except Exception as e:
                    result_queue.put((str(e), True))

            # Run the process in a background thread
            process_thread = threading.Thread(target=run_process)
            process_thread.start()
            # process_thread.join()  # Wait for the thread to finish will block main process


            return "Process started", False
        except Exception as e:
            result_queue.put((str(e), True))

    def execute_subprocessold(self, command, project_path,project_name):
        try:
            if is_windows:
                # On Windows, use subprocess directly without PTY
                process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=project_path, shell=True)
            else:
                # On Unix-like systems, use PTY
                master, slave = pty.openpty()
                process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=project_path, shell=True, preexec_fn=os.setsid)
                os.close(slave)  # Close the slave end in the parent process

            pid = process.pid

            # Store process information
            with self.lock:
                process_dict[pid] = process

            # Emit the process ID to the frontend
            emit_agent("pid", {"command": command, "pid": pid})

            # Store output incrementally
            output = ""

            # Function to read and handle output
            def read_output():
                nonlocal output
                if is_windows:
                    while True:
                        data = process.stdout.read(4096).decode('utf-8', errors='ignore')
                        if not data:
                            break
                        output += data
                        monologue = f"running the command '{command}': {output}"
                        self.update_state(project_name, command, output, monologue=monologue)
                else:
                    while True:
                        try:
                            data = os.read(master, 4096).decode('utf-8', errors='ignore')
                            if not data:
                                break
                            output += data
                            monologue = f"running the command '{command}': {output}"
                            self.update_state(project_name, command, output, monologue=monologue)
                        except OSError:
                            break

            output_thread = threading.Thread(target=read_output)
            output_thread.start()

            # Wait for the process to finish
            returncode = process.wait()

            # Ensure the output thread finishes
            output_thread.join()

            # Remove process from the dictionary
            with self.lock:
                del process_dict[pid]
            tes = "killed"
            emit_agent("pidkilled", {"command": tes, "pid": pid})
            return output, returncode != 0
        except Exception as e:
            return str(e), True

    def update_state(self, project_name, command, output, monologue="Running code..."):
        new_state = AgentState().new_state()
        new_state.update({
            "internal_monologue": monologue,
            "terminal_session": {
                "command": command,
                "output": output,
                "title": "Terminal"
            }
        })
        AgentState().add_to_current_state(project_name, new_state)

    def handle_rerun(self, commands, project_path, project_name, conversation, code_markdown, system_os, error_output, retries):
        prompt = self.render_rerunner(conversation, code_markdown, system_os, commands, error_output)
        response = self.llm.inference(prompt, project_name)
        valid_response = self.validate_rerunner_response(response)

        while not valid_response:
            print("Invalid response from the model, trying again...")
            return self.run_code(commands, project_path, project_name, conversation, code_markdown, system_os, retries)

        action = valid_response["action"]
        response_text = valid_response["response"]

        if action == "command":
            return valid_response["command"], response_text
        elif action == "patch":
            patcher = Patcher(base_model=self.base_model)
            new_code = patcher.execute(conversation, code_markdown, commands, error_output, system_os, project_name)
            patcher.save_code_to_project(new_code, project_name)
            print(commands[0])
            print(response_text)
            return commands[0], response_text  # Re-run the first command after patching

    def run_code(self, commands, project_path, project_name, conversation, code_markdown, system_os, retries=0):
        success = True
        result_queue = queue.Queue()
        for command in commands:
            self.execute_subprocess(command, project_path, project_name, result_queue)
            command_output, command_failed = result_queue.get()
            print(command_output)
            # self.update_state(project_name, command, command_output)

            while command_failed and retries < 2:
                success = False
                monologue = f"Oh, seems like there is some error with the command '{command}': {command_output}"
                self.update_state(project_name, command, command_output, monologue=monologue)
                time.sleep(1)
                command, response_text = self.handle_rerun(commands, project_path, project_name, conversation,
                                                           code_markdown, system_os, command_output, retries)
                ProjectManager().add_message_from_devika(project_name, response_text)

                self.execute_subprocess(command, project_path, project_name, result_queue)
                command_output, command_failed = result_queue.get()
                self.update_state(project_name, command, command_output)
                retries += 1 if command_failed else 0
                print(retries)

            if not command_failed:
                continue

        return success

    def execute(self, conversation, code_markdown, os_system, project_path, project_name):
        retries = 0
        valid_commands = None
        while retries < self.retry_limit:
            prompt = self.render(conversation, code_markdown, os_system)
            try:
                response = self.llm.inference(prompt, project_name)
                valid_commands = self.validate_response(response)
                if valid_commands:
                    success = self.run_code(valid_commands, project_path, project_name, conversation, code_markdown,
                                            os_system)
                    print("am here horray")
                    print(success)
                    if success:
                        break
            except DeadlineExceeded as e:
                self.logger.error(f"Deadline Exceeded error on attempt {retries + 1}: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error on attempt {retries + 1}: {e}")
            retries += 1
            print(f"Invalid response from the model, trying again... (Attempt {retries})")

        if retries == self.retry_limit:
            self.logger.error("Failed to get a valid response after multiple attempts.")
            return None

        return valid_commands

