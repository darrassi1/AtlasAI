import os





def terminate_process(pid):
    import signal
    from src.socket_instance import emit_agent
    from src.agents.runner.runner import process_dict, is_windows
    print(process_dict)  # Printing the process dictionary
    if pid in process_dict:
        process = process_dict[pid]
        try:
            if is_windows:
                process.terminate()  # Assuming the process object has a terminate method
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            emit_agent('kill_process_response', {"status": "success", "message": f"Process {pid} terminated."})
        except Exception as e:
            emit_agent('kill_process_response', {"status": "error", "message": str(e)})
    else:
        emit_agent('kill_process_response', {"status": "error", "message": f"Process {pid} not found."})

def shorten_path(path):
    """
  This function shortens a path by removing redundant directory structures.

  Args:
      path: The path to be shortened (string).

  Returns:
      The shortened path (string).
  """
    parts = path.split("/")  # Split the path into parts based on "/" separator
    shortened_path = []
    for part in parts:
        if part not in shortened_path:  # Add unique parts to the shortened path
            shortened_path.append(part)
    return "/".join(shortened_path)


def read_Sysdesign(project_dir, project_name):
    sstemdesign = "systemdesign"
    sstemdesign_txt = "systemdesign.txt"

    systemdesign_path = os.path.join(project_dir, project_name, sstemdesign, sstemdesign_txt)

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
        if not filenames:
            print(f"{systemdesign_path} is empty.")
    except Exception as e:
        print(f"An error occurred while reading {systemdesign_path}: {e}")

    return filenames
