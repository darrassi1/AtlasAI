import base64
import os
import time

import plantuml

from jinja2 import Environment, BaseLoader

from src.llm import LLM
from src.config import Config
from src.project import ProjectManager

PROMPT = open("src/agents/drawuml/prompt.jinja2").read().strip()


class Drawuml:
    def __init__(self, base_model: str):
        self.project_manager = ProjectManager()
        self.llm = LLM(model_id=base_model)
        config = Config()
        self.project_dir = config.get_projects_dir()

    def render(self, prompt: str, code_markdown: str, diagram: str) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(prompt=prompt, code_markdown=code_markdown, diagram=diagram)

    def validate_response(self, response: str) -> bool | list[str]:
        response = response.strip()

        if not (response.startswith("~~~") and response.endswith("~~~")):
            return False

        response = response[3:-3].strip().split('\n')

        return response

    def get_image_as_base64_string(self, image_path: str):
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/png;base64,{encoded_string}"

    def execute(self, prompt: str, code_markdown: str, project_name: str) -> None:
        diagram_types = ["Class", "Sequence", "UseCase", "Activite", "Composant", "Etat", "Objet", "Deploiement",
                         "Temps"]
        systemdesign_folder = os.path.join(self.project_dir, project_name, "systemdesign", "uml")

        # Ensure systemdesign folder exists
        os.makedirs(systemdesign_folder, exist_ok=True)

        for item in diagram_types:
            rendered_prompt = self.render(prompt, code_markdown, item)
            response = self.llm.inference(rendered_prompt, project_name)

            valid_response = self.validate_response(response)
            if not valid_response:
                print("Invalid response from drawuml the model, trying again...")
                continue

            # Create appropriate filename based on item content
            filename = f"{item}.puml"
            filepath = os.path.join(systemdesign_folder, filename)

            # Write valid response to puml file
            with open(filepath, "w") as f:
                f.write('\n'.join(valid_response))

            # Generate PNG image using PlantUML with error handling
            try:
                plantuml_plantuml = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/png/')
                plantuml_plantuml.processes_file(filepath)
                print(f"Generated UML diagram: {filepath[:-5]}.png")

                # Convert the PNG file to a Base64 string
                image_string = self.get_image_as_base64_string(f"{filepath[:-5]}.png")
                diagrammed = f"Diagram De {item}"
                #time.sleep(4)
                self.project_manager.add_message_from_devika(project_name, diagrammed)
                # Send the image string to the frontend
                self.project_manager.add_message_from_devika(project_name, image_string)

            except Exception as e:
                print(f"Error generating PNG: {e}")

        # Return value remains None as a success indicator
