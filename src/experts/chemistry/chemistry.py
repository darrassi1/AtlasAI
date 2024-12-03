import base64
import json
import time
from rdkit import Chem
from rdkit.Chem import Draw, rdMolDescriptors
from jinja2 import Environment, BaseLoader

from src.llm import LLM

PROMPT = open("src/experts/chemistry/prompt.jinja2").read().strip()


class Chemistry:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)

    def render(self, prompt: str) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(prompt=prompt)

    def validate_response(self, response: str):
        response = response.strip().replace("```json", "```")

        if response.startswith("'''") and response.endswith("'''"):
            response = response[3:-3].strip()



        return response

    def parse_smile(self, smile_notation):
        try:
            mol = Chem.MolFromSmiles(smile_notation)
            if mol is None:
                return None  # Return None if SMILES notation is invalid
            return mol
        except Exception as e:
            raise ValueError(f"Error parsing SMILES: {str(e)}")
    def get_molecule_properties(self, molecule):
        properties = {}
        try:
            properties['num_atoms'] = molecule.GetNumAtoms()
            properties['num_bonds'] = molecule.GetNumBonds()
            properties['formula'] = rdMolDescriptors.CalcMolFormula(molecule)
            properties['molecular_weight'] = rdMolDescriptors.CalcExactMolWt(molecule)

            #self.logger.info("Successfully retrieved molecule properties.")
        except Exception as e:
            #self.logger.exception("Error calculating molecule properties.")
            raise ValueError(f"Error calculating molecule properties: {str(e)}")
        return properties
    def print_molecule_properties(self, properties):
        try:
            prop_dict = {}
            for prop, value in properties.items():
                prop_dict[f"{prop.replace('_', ' ').capitalize()}"] = value
            return prop_dict
        except Exception as e:
            raise ValueError(f"Error printing molecule properties: {str(e)}")
    def generate_filename(self, molecule, img_format):
        formula = rdMolDescriptors.CalcMolFormula(molecule)
        timestamp = time.strftime("%Y%m%d%H%M%S")
        filename = f"{formula}_{timestamp}.{img_format}"
        return filename
    def visualize_molecule(self, molecule, filename=None, img_format="png"):
        try:
            if filename is None:
                filename = self.generate_filename(molecule, img_format)
            if img_format.lower() not in ["png", "svg"]:
                #self.logger.error("Unsupported image format: %s", img_format)
                raise ValueError("Unsupported image format. Please use 'png' or 'svg'.")
            # Ensure the molecule is drawn with colors
            options = Draw.MolDrawOptions()
            options.useBWAtomPalette = False  # Ensure colors are used
            if img_format.lower() == "png":
                drawer = Draw.MolDraw2DCairo(300, 300)  # for PNG format
                drawer.SetDrawOptions(options)
                drawer.DrawMolecule(molecule)
                drawer.FinishDrawing()
                image_bytes = drawer.GetDrawingText()
            else:
                drawer = Draw.MolDraw2DSVG(300, 300)  # for SVG format
                drawer.SetDrawOptions(options)
                drawer.DrawMolecule(molecule)
                drawer.FinishDrawing()
                image_bytes = drawer.GetDrawingText().encode('utf-8')
            return image_bytes

            #self.logger.info("Molecule image saved to %s", filename)
        except Exception as e:
            #self.logger.exception("Error visualizing molecule.")
            raise ValueError(f"Error visualizing molecule: {str(e)}")

    import re

    def parse_response(self, response: str):
        parsed_data = {
            "Problem Description": "",
            "plans": {},
            "Innovative Solutions": "",
            "smile_annotations": []  # Initialize an empty list for smile annotations
        }

        lines = response.split("\n")
        current_section = None
        current_step = None

        for line in lines:
            line = line.strip()

            if line.startswith("Problem Description:"):
                current_section = "Problem Description"
                parsed_data[current_section] = line.split(":", 1)[1].strip()
            elif line.startswith("Plan:"):
                current_section = "plans"
            elif line.startswith("Innovative Solutions:"):
                current_section = "Innovative Solutions"
                parsed_data[current_section] = line.split(":", 1)[1].strip()
            elif current_section == "Problem Description":
                parsed_data[current_section] += " " + line
            elif current_section == "plans":
                if line.startswith("- Step"):
                    try:
                        current_step = int(line.split(":")[0].strip().split(" ")[-1])
                        # Extract content between second and third occurrences of ":"
                        step_parts = line.split(":")
                        if len(step_parts) >= 4:
                            smile_annotation = step_parts[2].strip()
                            print(smile_annotation)
                            parsed_data["smile_annotations"].append(smile_annotation)  # Add to the list
                        parsed_data[current_section][current_step] = line.split(":", 1)[1].strip()
                    except (ValueError, IndexError):
                        print(f"Error: Malformed plan step line: {line}")
                        current_step = None
                elif current_step is not None:
                    parsed_data[current_section][current_step] += " " + line
            elif current_section == "Innovative Solutions":
                parsed_data[current_section] += " " + line

        # Strip any leading/trailing whitespace from all string values
        parsed_data = {k: v.strip() if isinstance(v, str) else v for k, v in parsed_data.items()}

        return parsed_data

    def execute(self, prompt: str, project_name: str) -> str:
        rendered_prompt = self.render(prompt)
        response = self.llm.inference(rendered_prompt, project_name)

        valid_response = self.validate_response(response)

        while not valid_response:
            print("Invalid response from the model, trying again...")
            return self.execute(prompt, project_name)

        #mol = self.parse_smile(smile)
        #properties = self.get_molecule_properties(mol)
        #self.print_molecule_properties(properties)
        #self.visualize_molecule(mol, img_format="png")

        return valid_response