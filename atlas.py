"""
    DO NOT REARRANGE THE ORDER OF THE FUNCTION CALLS AND VARIABLE DECLARATIONS
    AS IT MAY CAUSE IMPORT ERRORS AND OTHER ISSUES
"""
import json
import shutil

from gevent import monkey


monkey.patch_all()
from src.init import init_devika

init_devika()

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from src.socket_instance import socketio, emit_agent
import os
import logging
from threading import Thread
import tiktoken

from src.apis.project import project_bp
from src.config import Config
from src.logger import Logger, route_logger
from src.project import ProjectManager
from src.state import AgentState
from src.agents import Agents
from src.agents.iaedit import Iaedit
from src.agents.hyperparametre import Hyperparametre
from src.llm import LLM


app = Flask(__name__)
CORS(app)
app.register_blueprint(project_bp)
socketio.init_app(app)

log = logging.getLogger("werkzeug")
log.disabled = True

TIKTOKEN_ENC = tiktoken.get_encoding("cl100k_base")

os.environ["TOKENIZERS_PARALLELISM"] = "false"

manager = ProjectManager()
AgentState = AgentState()
config = Config()
logger = Logger()
project_dir = config.get_projects_dir()


# initial socket
@socketio.on("socket_connect")
def test_connect(data):
    print("Socket connected :: ", data)
    emit_agent("socket_response", {"data": "Server Connected"})


@app.route("/api/data", methods=["GET"])
@route_logger(logger)
def data():
    project = manager.get_project_list()
    models = LLM().list_models()
    search_engines = ["Bing", "Google", "DuckDuckGo"]
    return jsonify(
        {"projects": project, "models": models, "search_engines": search_engines}
    )


@app.route('/api/codeeditorsave', methods=['POST'])
def update_code():
    data = request.json
    filename = data.get("filename")
    project_name = data.get("project_name")
    content = data.get("content")
    print(project_name)
    construct_path = os.path.join(project_dir, project_name, filename)

    # Update the file with the new content
    with open(construct_path, 'w') as file:
        file.write(content)
        print("happy am here")
        print(construct_path)

    return jsonify({'message': 'File updated successfully'})


@app.route("/api/messages", methods=["POST"])
def get_messages():
    data = request.json
    project_name = data.get("project_name")
    messages = manager.get_messages(project_name)
    return jsonify({"messages": messages})


@app.route('/api/hyperparametre', methods=['POST'])
def save_hyperparametre():
    data = request.json
    temperature = data.get('temperature')
    max_token = data.get('maxToken')
    top_p = data.get('topP')
    # Updating inference settings
    config.set_temperature(temperature)
    config.set_max_token(max_token)
    config.set_top_p(top_p)
    base_model = data.get("base_model")
    project_name = data.get("project_name")
    hyper = Hyperparametre(base_model=base_model)
    hyperrep = hyper.execute(temperature, max_token, top_p, project_name)
    ProjectManager().add_message_from_devika(project_name, hyperrep)
    print(f"Current temperature: {temperature}")
    print(f"Current max token: {max_token}")
    print(f"Current top P: {top_p}")

    # Optionally, perform additional logic like saving to database

    return jsonify({'message': 'Settings saved successfully'})


@app.route('/api/code-suggestions', methods=['POST'])
def get_code_suggestions():
    data = request.get_json()
    language = data.get('language')
    code = data.get('code')
    base_model = data.get("base_model")
    project_name = data.get("project_name")

    iaedit = Iaedit(base_model=base_model)
    # Replace this with your actual rectification logic
    suggestions = iaedit.autocompletion(language, code, project_name)
    print(" code suggestions backend")
    print("                        ")
    print("                        ")
    print("                        ")
    print(code)
    print(language)
    print(suggestions)
    # Dummy logic to return code suggestions based on language
    # if language in code_suggestions:
    #    suggestions = code_suggestions[language]
    # else:
    # suggestions = []
    # Convert code_suggestions to JSON format
    # suggestions_json = json.dumps({'suggestions': code_suggestions})

    return jsonify({'suggestions': suggestions})


@app.route('/rectify', methods=['POST'])
def rectify_code():
    data = request.json
    code = data.get('code')
    prompt = data.get('prompt')
    base_model = data.get("base_model")
    project_name = data.get("project_name")

    iaedit = Iaedit(base_model=base_model)
    # Replace this with your actual rectification logic
    rectified_code = iaedit.rectify_code_function(prompt, code, project_name)

    return jsonify({'rectifiedCode': rectified_code})


# Main socket
@socketio.on("user-message")
def handle_message(data):
    action = data.get("action")
    message = data.get("message")
    base_model = data.get("base_model")
    project_name = data.get("project_name")
    search_engine = data.get("search_engine").lower()
    selected_files = data.get("selected_files")

    agent = Agents(base_model=base_model, search_engine=search_engine)

    if action == "continue":
        new_message = manager.new_message("")
        new_message["message"] = message
        new_message["from_devika"] = False
        manager.add_message_from_user(project_name, new_message["message"])
        # if AgentState.is_agent_completed(project_name):
        #if AgentState.is_agent_completed(project_name):
        thread = Thread(
                target=lambda: agent.subsequent_execute(message, project_name))
        thread.start()
        #else:
        #    emit_agent("info", {"type": "warning",
         #                       "message": "previous agent doesn't completed it's task."})
    if action == "execute_chemistry":
        new_message = manager.new_message("")
        new_message["message"] = message
        new_message["from_devika"] = False
        manager.add_message_from_user(project_name, new_message["message"])
        # if AgentState.is_agent_completed(project_name):
        if AgentState.is_agent_completed(project_name):
            thread = Thread(
                target=lambda: agent.chemistry_expert(message, project_name)
            )
            thread.start()
        else:
            emit_agent("info", {"type": "warning",
                                "message": "previous agent doesn't completed it's task."})
    if action == "execute_logo":
        new_message = manager.new_message("")
        new_message["message"] = message
        new_message["from_devika"] = False
        manager.add_message_from_user(project_name, new_message["message"])
        # if AgentState.is_agent_completed(project_name):
        if AgentState.is_agent_completed(project_name):
            thread = Thread(
                target=lambda: agent.logo_expert(message, project_name)
            )
            thread.start()
        else:
            emit_agent("info", {"type": "warning",
                                "message": "previous agent doesn't completed it's task."})
    if action == "incdev":
        new_message = manager.new_message("")
        new_message["message"] = message
        new_message["from_devika"] = False
        manager.add_message_from_user(project_name, new_message["message"])
        if AgentState.is_agent_completed(project_name):
            thread = Thread(
                target=lambda: agent.inc_dev(message, selected_files, project_name)
            )
            thread.start()
        else:
            emit_agent("info", {"type": "warning",
                                "message": "previous agent doesn't completed it's task."})
    if action == "debugselectedfile":
        new_message = manager.new_message("")
        new_message["message"] = message
        new_message["from_devika"] = False
        manager.add_message_from_user(project_name, new_message["message"])
        if AgentState.is_agent_completed(project_name):
            thread = Thread(
                target=lambda: agent.debugselectedfile(message, selected_files, project_name)
            )
            thread.start()
        else:
            emit_agent("info", {"type": "warning",
                                "message": "previous agent doesn't completed it's task."})
    if action == "continue1":
        new_message = manager.new_message("")
        new_message["message"] = message
        new_message["from_devika"] = False
        manager.add_message_from_user(project_name, new_message["message"])
        # if AgentState.is_agent_completed(project_name):

        thread = Thread(target=lambda: agent.subsequent_execute(message, project_name))
        thread.start()

    if action == "execute_agent":
        thread = Thread(target=lambda: agent.execute(message, project_name))
        thread.start()


@app.route("/api/is-agent-active", methods=["POST"])
@route_logger(logger)
def is_agent_active():
    data = request.json
    project_name = data.get("project_name")
    is_active = AgentState.is_agent_active(project_name)
    return jsonify({"is_active": is_active})


@app.route("/api/get-agent-state", methods=["POST"])
@route_logger(logger)
def get_agent_state():
    data = request.json
    project_name = data.get("project_name")
    agent_state = AgentState.get_latest_state(project_name)
    return jsonify({"state": agent_state})


@app.route("/api/get-project-files/", methods=["GET"])
@route_logger(logger)
def project_files():
    project_name = request.args.get("project_name")
    files = AgentState.get_project_files(project_name)
    return jsonify({"files": files})


@app.route("/api/get-browser-snapshot", methods=["GET"])
@route_logger(logger)
def browser_snapshot():
    snapshot_path = request.args.get("snapshot_path")
    return send_file(snapshot_path, as_attachment=True)


@app.route("/api/get-browser-session", methods=["GET"])
@route_logger(logger)
def get_browser_session():
    project_name = request.args.get("project_name")
    agent_state = AgentState.get_latest_state(project_name)
    if not agent_state:
        return jsonify({"session": None})
    else:
        browser_session = agent_state["browser_session"]
        return jsonify({"session": browser_session})


@app.route("/api/get-terminal-session", methods=["GET"])
@route_logger(logger)
def get_terminal_session():
    project_name = request.args.get("project_name")
    agent_state = AgentState.get_latest_state(project_name)
    if not agent_state:
        return jsonify({"terminal_state": None})
    else:
        terminal_state = agent_state["terminal_session"]
        return jsonify({"terminal_state": terminal_state})


@app.route("/api/run-code", methods=["POST"])
@route_logger(logger)
def run_code():
    data = request.json
    project_name = data.get("project_name")
    code = data.get("code")
    # TODO: Implement code execution logic
    return jsonify({"message": "Code execution started"})


@app.route("/api/calculate-tokens", methods=["POST"])
@route_logger(logger)
def calculate_tokens():
    data = request.json
    prompt = data.get("prompt")
    tokens = len(TIKTOKEN_ENC.encode(prompt))
    return jsonify({"token_usage": tokens})


@app.route("/api/token-usage", methods=["GET"])
@route_logger(logger)
def token_usage():
    project_name = request.args.get("project_name")
    token_count = AgentState.get_latest_token_usage(project_name)
    return jsonify({"token_usage": token_count})


@app.route("/api/logs", methods=["GET"])
def real_time_logs():
    log_file = logger.read_log_file()
    return jsonify({"logs": log_file})


@app.route("/api/settings", methods=["POST"])
@route_logger(logger)
def set_settings():
    data = request.json
    print("Data: ", data)
    config.config.update(data)
    config.save_config()
    return jsonify({"message": "Settings updated"})


@app.route("/api/settings", methods=["GET"])
@route_logger(logger)
def get_settings():
    configs = config.get_config()
    return jsonify({"settings": configs})


# Directory where files will be stored


@app.route('/api/files/create', methods=['POST'])
def create_file():
    try:
        data = request.get_json()
        filename = data['filename']
        project_name = data['projectName']
        project_path = os.path.join(project_dir, project_name)
        os.makedirs(project_path, exist_ok=True)
        file_path = os.path.join(project_path, filename)

        # Create the file if it doesn't exist
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write('')
            return jsonify({"message": "File created successfully"}), 201
        else:
            return jsonify({"message": "File already exists"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/files/rename', methods=['PUT'])
def rename_file():
    try:
        data = request.get_json()
        old_name = data['oldName']
        new_name = data['newName']
        project_name = data['projectName']
        project_path = os.path.join(project_dir, project_name)
        # Remove leading slashes from the new name
        new_name = new_name.lstrip('/\\')
        old_path = os.path.join(project_path, old_name)
        new_path = os.path.join(project_path, new_name)
        normalized_old_path = os.path.normpath(old_path)
        normalized_new_path = os.path.normpath(new_path)

        # Rename the file if it exists
        if os.path.exists(normalized_old_path):
            if os.path.splitext(normalized_new_path)[1]:
                # Create the parent directory
                parent_dir = os.path.dirname(normalized_new_path)
                os.makedirs(parent_dir, exist_ok=True)
                os.rename(normalized_old_path, normalized_new_path)
            else:
                # os.makedirs(normalized_new_path, exist_ok=True)
                os.rename(normalized_old_path, normalized_new_path)
                # AgentState.add_placeholder_to_empty_folders(project_name)
                # Rename the file if it exists and paths are different
                # if normalized_old_path != normalized_new_path:
                # os.rename(normalized_old_path, normalized_new_path)
                #    print("Renamed successfully")
                # else:
                #   print("Paths are the same; no renaming needed")

            AgentState.add_placeholder_to_empty_folders(project_name)
            return jsonify({"message": "File renamed successfully"}), 200
        else:
            return jsonify({"message": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/files/delete', methods=['DELETE'])
def delete_file():
    try:
        data = request.get_json()
        filename = data['filename']
        project_name = data['projectName']
        project_path = os.path.join(project_dir, project_name)
        file_path = os.path.join(project_path, filename)
        file_path1 = os.path.normpath(file_path)
        # Delete the file if it exists

        if os.path.isfile(file_path1):
            os.remove(file_path1)
            AgentState.add_placeholder_to_empty_folders(project_name)
            return jsonify({"message": "File deleted successfully"}), 200

        elif os.path.isdir(file_path1):
            shutil.rmtree(file_path1)  # Remove the directory and its contents
            AgentState.add_placeholder_to_empty_folders(project_name)
            return jsonify({"message": "Directory deleted successfully"}), 200



        else:
            return jsonify({"message": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    logger.info("Atlas is up and running!")
    socketio.run(app, debug=True, port=1337, host="0.0.0.0")
