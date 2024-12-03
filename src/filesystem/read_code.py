import os
from src.config import Config

class ReadCode:
    def __init__(self, project_name: str):
        config = Config()
        project_path = config.get_projects_dir()
        self.project_dir = project_path
        self.directory_path = os.path.join(project_path, project_name.lower().replace(" ", "-"))

    def read_directory(self):
        files_list = []
        excluded_dirs = ['.git', 'systemdesign', '.idea', '.venv', 'node_modules', 'build', 'coverage', 'venv']
        excluded_files = ['.placeholder', 'newFile.js', 'favicon.ico', 'README.md', '.gitignore', 'LICENSE']
        excluded_file_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico', '.json', '.svg','.txt']

        for root, dirs, files in os.walk(self.directory_path):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            for file in files:
                if file in excluded_files or any(file.lower().endswith(ext) for ext in excluded_file_extensions):
                    continue
                try:
                    file_path = os.path.join(root, file)
                    relative_file_path = os.path.relpath(file_path, self.project_dir)
                    with open(file_path, 'r') as file_content:
                        files_list.append({"filename": relative_file_path, "code": file_content.read().strip()})
                except:
                    pass
        return files_list

    def code_set_to_markdown(self):
        code_set = self.read_directory()
        markdown = "\n".join([f"{code['filename']}:\n```\n{code['code']}\n```" for code in code_set])
        print(markdown.strip())
        return markdown.strip()
