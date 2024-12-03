import asyncio
import os
import platform
import subprocess
import threading

is_windows = platform.system() == 'Windows'

if not is_windows:
    import pty

process_dict = {}


class Runner:
    def __init__(self):
        self.lock = threading.Lock()

    # Use this method to start a long-running process like a React server
    def start_server(self, project_path, project_name):
        command = "bun run dev"  # or whatever command starts your React server
        asyncio.run(self.run_long_running_process(command, project_path, project_name))

    async def run_long_running_process(self, command, project_path, project_name):
        output, error = await self.execute_long_running_subprocess(command, project_path, project_name)
        if error:
            print(f"Error running command: {output}")
        else:
            print(f"Command completed successfully: {output}")

    async def execute_long_running_subprocess(self, command, project_path, project_name):
        try:
            if is_windows:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=project_path
                )
            else:
                master, slave = pty.openpty()
                process = await asyncio.create_subprocess_exec(
                    *command.split(),
                    stdout=slave,
                    stderr=slave,
                    stdin=slave,
                    cwd=project_path,
                    preexec_fn=os.setsid
                )
                os.close(slave)

            pid = process.pid

            # Store process information
            with self.lock:
                process_dict[pid] = process

            # Emit the process ID to the frontend
            emit_agent("pid", {"command": command, "pid": pid})

            async def read_output():
                while True:
                    if is_windows:
                        line = await process.stdout.readline()
                    else:
                        try:
                            line = await asyncio.to_thread(os.read, master, 4096)
                        except OSError:
                            break

                    if not line:
                        break

                    output = line.decode('utf-8', errors='ignore')
                    monologue = f"running the command '{command}': {output}"
                    self.update_state(project_name, command, output, monologue=monologue)

            # Start reading output in a separate task
            asyncio.create_task(read_output())

            # Wait for the process to finish (this will keep the server running)
            await process.wait()

            # Process has finished
            with self.lock:
                del process_dict[pid]
            emit_agent("pidkilled", {"command": "killed", "pid": pid})

            return "Process completed", False
        except Exception as e:
            return str(e), True

    def update_state(self, project_name, command, output, monologue=""):
        print(f"Update State: Project: {project_name}, Command: {command}, Output: {output}, Monologue: {monologue}")


def emit_agent(event_type, data):
    print(f"Event: {event_type}, Data: {data}")


def main():
    runner = Runner()
    project_path = "ui"  # Replace with your project path
    project_name = "MyReactApp"

    # Start the server
    runner.start_server(project_path, project_name)


if __name__ == "__main__":
    main()
