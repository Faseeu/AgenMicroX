import os
import base64
import requests
from PIL import Image
from io import BytesIO
from duckduckgo_search import AsyncDDGS
from agency_swarm.tools import BaseTool
from pydantic import Field
from agency_swarm import Agent, Agency, set_openai_client
from litellm import LiteLLM
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML

# Tools
class EncodeImageTool(BaseTool):
    image_path: str = Field(..., description="Path to the image file.")
    
    def run(self):
        try:
            with open(self.image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            return None
        except IOError:
            return None

class ValidateImageURLTool(BaseTool):
    url: str = Field(..., description="URL of the image to validate.")
    
    def run(self):
        try:
            response = requests.get(
                self.url, 
                stream=True, 
                timeout=5,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '').lower()
            if content_type.startswith(('image/', 'application/octet-stream')):
                return True

            image = Image.open(BytesIO(response.content))
            image.verify()
            return True

        except requests.exceptions.RequestException as e:
            return f"Network error: {e}"
        except Image.UnidentifiedImageError:
            return "The URL doesn't point to a valid image."
        except Exception as e:
            return f"Unexpected error: {e}"

class SearchTool(BaseTool):
    query: str = Field(..., description="Search query.")
    
    async def run(self):
        results = await AsyncDDGS(proxy=None).atext(self.query, max_results=100)
        return results

class WriteFileTool(BaseTool):
    filepath: str = Field(..., description="Path to the file.")
    content: str = Field(..., description="Content to write to the file.")

    def run(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write(self.content)
            return True
        except IOError as e:
            return f"Error writing to {self.filepath}: {e}"

class ReadFileTool(BaseTool):
    filepath: str = Field(..., description="Path to the file.")

    def run(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return f"Error: File not found: {self.filepath}"
        except IOError as e:
            return f"Error reading {self.filepath}: {e}"

class InitializeProjectTool(BaseTool):
    project_name: str = Field(..., description="Name of the project to initialize.")
    directory: str = Field(..., description="Directory where the project should be created.")

    def run(self):
        project_path = os.path.join(self.directory, self.project_name)
        try:
            os.makedirs(project_path, exist_ok=True)
            return f"Project {self.project_name} initialized at {project_path}"
        except OSError as e:
            return f"Error creating project directory: {e}"

class CheckDirectoryTool(BaseTool):
    directory: str = Field(..., description="Directory to check.")

    def run(self):
        if os.path.exists(self.directory):
            return f"Directory {self.directory} exists."
        else:
            return f"Directory {self.directory} does not exist."

class InstallDependenciesTool(BaseTool):
    requirements_file: str = Field(..., description="Path to the requirements.txt file.")

    def run(self):
        try:
            os.system(f"pip install -r {self.requirements_file}")
            return f"Dependencies installed from {self.requirements_file}."
        except Exception as e:
            return f"Error installing dependencies: {e}"

class EditFileTool(BaseTool):
    filepath: str = Field(..., description="Path to the file.")
    content: str = Field(..., description="New content to replace in the file.")
    start_marker: str = Field(..., description="Marker where the edit starts.")
    end_marker: str = Field(..., description="Marker where the edit ends.", default=None)

    def run(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            start_idx = None
            end_idx = None
            for idx, line in enumerate(lines):
                if self.start_marker in line:
                    start_idx = idx
                if self.end_marker and self.end_marker in line:
                    end_idx = idx

            if start_idx is not None:
                if end_idx is not None:
                    lines = lines[:start_idx + 1] + [self.content + '\n'] + lines[end_idx:]
                else:
                    lines[start_idx] = self.content + '\n'
                with open(self.filepath, 'w', encoding='utf-8') as file:
                    file.writelines(lines)
                return f"File {self.filepath} edited successfully."
            else:
                return f"Markers not found in {self.filepath}."
        except Exception as e:
            return f"Error editing {self.filepath}: {e}"

class DebugTool(BaseTool):
    filepath: str = Field(..., description="Path to the file to debug.")

    def run(self):
        try:
            # Replace this with actual debugging logic
            os.system(f"python -m pdb {self.filepath}")
            return f"Debugging initiated for {self.filepath}."
        except Exception as e:
            return f"Error debugging {self.filepath}: {e}"

class CheckCodeAlignmentTool(BaseTool):
    directory: str = Field(..., description="Directory where the project code is stored.")

    def run(self):
        try:
            # This is a placeholder for actual code alignment checking logic.
            return f"Code alignment checked for the directory {self.directory}."
        except Exception as e:
            return f"Error checking code alignment: {e}"

# Senior Developer Agent
class SeniorDeveloperAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Senior Developer",
            description="I oversee the development process, guide developer agents, and ensure that the code adheres to the plan.",
            model="groq/llama-3.1-70b-versatile",
            instructions="",
            tools=[
                EncodeImageTool, ValidateImageURLTool, SearchTool,
                WriteFileTool, ReadFileTool, InitializeProjectTool,
                CheckDirectoryTool, InstallDependenciesTool,
                EditFileTool, DebugTool, CheckCodeAlignmentTool
            ],
            temperature=0.5,
            max_prompt_tokens=25000
        )

# Set up LiteLLM client

# Initialize your agents
senior_developer = SeniorDeveloperAgent()

# 
# Command completion and history
commands = WordCompleter([
    '/add', '/edit', '/new', '/search', '/image', '/clear',
    '/reset', '/diff', '/history', '/save', '/load', '/undo',
    '/init', '/checkdir', '/install', '/edit', '/debug', '/check',
    'exit'
], ignore_case=True)
command_history = FileHistory('.aiconsole_history.txt')
session = PromptSession(history=command_history)

async def get_input_async(message):
    result = await session.prompt_async(HTML(f"<ansired>{message}</ansired> "),
        auto_suggest=AutoSuggestFromHistory(),
        completer=commands,
        refresh_interval=0.5)
    return result.strip()

async def handle_commands():
    while True:
        command = await get_input_async("Enter command: ")

        if command.startswith("/add "):
            filepaths = command.split("/add ", 1)[1].strip().split()
            for path in filepaths:
                content = await senior_developer.run_tool("ReadFileTool", filepath=path)
                await senior_developer.run_tool("WriteFileTool", filepath=path, content=content)
            continue

        elif command.startswith("/edit "):
            filepath = command.split("/edit ", 1)[1].strip()
            start_marker = await get_input_async(f"Enter the start marker for editing {filepath}: ")
            end_marker = await get_input_async(f"Enter the end marker (optional) for editing {filepath}: ")
            content = await get_input_async(f"Enter the new content for {filepath}: ")
            result = await senior_developer.run_tool("EditFileTool", filepath=filepath, content=content, start_marker=start_marker, end_marker=end_marker)
            print(result)
            continue

        elif command.startswith("/new "):
            filepath = command.split("/new ", 1)[1].strip()
            await senior_developer.run_tool("WriteFileTool", filepath=filepath, content="")
            continue

        elif command.startswith("/search "):
            query = command.split("/search ", 1)[1].strip()
            search_results = await senior_developer.run_tool("SearchTool", query=query)
            print(f"Search results: {search_results}")
            continue

        elif command.startswith("/init "):
            project_name, directory = command.split("/init ", 1)[1].strip().split()
            result = await senior_developer.run_tool("InitializeProjectTool", project_name=project_name, directory=directory)
            print(result)
            continue

        elif command.startswith("/checkdir "):
            directory = command.split("/checkdir ", 1)[1].strip()
            result = await senior_developer.run_tool("CheckDirectoryTool", directory=directory)
            print(result)
            continue

        elif command.startswith("/install "):
            requirements_file = command.split("/install ", 1)[1].strip()
            result = await senior_developer.run_tool("InstallDependenciesTool", requirements_file=requirements_file)
            print(result)
            continue

        elif command.startswith("/debug "):
            filepath = command.split("/debug ", 1)[1].strip()
            result = await senior_developer.run_tool("DebugTool", filepath=filepath)
            print(result)
            continue

        elif command.startswith("/check "):
            directory = command.split("/check ", 1)[1].strip()
            result = await senior_developer.run_tool("CheckCodeAlignmentTool", directory=directory)
            print(result)
            continue

        elif command == "exit":
            print("Exiting...")
            break

        else:
            response = await senior_developer.run_tool("SomeDefaultTool", command=command)
            print(f"Assistant: {response}")

# Run the main loop
async def main():
    await handle_commands()
    
