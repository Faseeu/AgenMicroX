import os
import base64
import requests
from PIL import Image
from io import BytesIO
from duckduckgo_search import AsyncDDGS
from agency_swarm.tools import BaseTool
from pydantic import Field, validator
from agency_swarm import Agent, Agency, set_openai_client
from litellm import LiteLLM
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML

# Tools

class CreateAgencyTool(BaseTool):
    """
    Tool to create a new development agency with a specified number of developers.

    Args:
        agency_name (str): The name to assign to the newly created agency.
        num_developers (int): The number of ExpertDeveloperAgent instances to create within the agency.

    Returns:
        None
    """
    agency_name: str = Field(..., description="The name to assign to the newly created agency.")
    num_developers: int = Field(..., description="The number of developers to include in the agency.")

    def run(self):
        from dev_agency_template.development_agency import ExpertDeveloperAgent, VerifierAgent, DevelopmentAgency

        verifier = VerifierAgent()
        developers = [ExpertDeveloperAgent() for _ in range(self.num_developers)]
        agency = DevelopmentAgency(verifier, developers)
        self.development_agencies[self.agency_name] = agency
        return f"Agency '{self.agency_name}' created with {self.num_developers} developers."

class AssignPlanToAgencyTool(BaseTool):
    """
    Tool to assign a development plan to an existing agency.

    Args:
        agency_name (str): The name of the agency to assign the plan to.
        plan (Plan): The development plan to assign, which will be converted to JSON format.

    Returns:
        str: Confirmation message indicating whether the plan was successfully assigned.
    """
    agency_name: str = Field(..., description="The name of the agency to assign the plan to.")
    plan: dict = Field(..., description="The development plan to assign to the agency in dictionary format.")

    def run(self):
        agency = self.development_agencies.get(self.agency_name)
        if agency:
            agency.receive_plan(self.plan)
            return f"Plan assigned to agency '{self.agency_name}'."
        return f"Agency '{self.agency_name}' not found."




class ModifyMainPyTool(BaseTool):
    """
    Tool to append code to the 'main.py' file, ensuring that any modifications are validated before being applied.
    
    Args:
        code_to_add (str): The code to append to the 'main.py' file. This code should be thoroughly validated and not contain any placeholders.
    
    Returns:
        str: Confirmation message indicating the code has been successfully added to 'main.py' or an error message if the process fails.
    """
    code_to_add: str = Field(..., description="The code to append to the 'main.py' file.")

    @validator('code_to_add')
    def validate_code(cls, v):
        # Ensure the code does not contain placeholders and is properly formatted
        if "placeholder" in v:
            raise ValueError("Code contains placeholders. Please provide complete and functional code"
class ImplementCodeTool(BaseTool):
    """
    Tool to implement and verify code from a specified agency. This tool collects the code, verifies its integrity,
    and then writes it to the appropriate files if it passes validation.

    Args:
        agency_name (str): The name of the agency from which to implement code.

    Returns:
        str: Result message indicating the success or failure of the code implementation process.
    """
    agency_name: str = Field(..., description="The name of the agency to implement code from.")

    def run(self):
        agency = self.development_agencies.get(self.agency_name)
        if not agency:
            return f"Error: Agency '{self.agency_name}' not found."

        try:
            # Collect the code from the agency
            code_submission = agency.collect_code()

            # Verify the collected code
            verified = agency.verify_and_finalize_code(code_submission)
            if not verified:
                return f"Code verification failed for '{self.agency_name}'."

            # Write the verified code to the appropriate files
            for file in code_submission.files:
                with open(file.file_name, 'w') as f:
                    f.write(file.code)

            return f"Code from '{self.agency_name}' successfully implemented."

        except Exception as e:
            return f"Error during code implementation for agency '{self.agency_name}': {e}'nal code'.")
        if not v.strip():
            raise ValueError("Code to add cannot be empty.")
        return v

    def run(self):
        try:
            # Check if 'main.py' exists
            if not os.path.exists("main.py"):
                return "Error: 'main.py' does not exist."

            # Append the validated code to 'main.py'
            with open("main.py", "a") as f:
                f.write(f"\n{self.code_to_add}")

            return "Code successfully added to 'main.py'."

        except Exception as e:
            return f"Error while modifying 'main.py': {e}"


class HandleTerminalCommandTool(BaseTool):
    """
    Tool to handle specific terminal commands related to functionality and agency management.

    Args:
        command (str): The terminal command to execute.

    Returns:
        str: Result of the executed command.
    """
    command: str = Field(..., description="The terminal command to execute.")

    def run(self):
        if self.command.startswith("/add functionality/"):
            # Add specific functionality to main.py
            functionality_code = "# Functionality added by Senior Developer Agent\n"
            ModifyMainPyTool(code_to_add=functionality_code).run()
            return "Functionality added to 'main.py'."

        elif self.command.startswith("/add improvement/"):
            # Add specific improvements to main.py
            improvement_code = "# Improvement added by Senior Developer Agent\n"
            ModifyMainPyTool(code_to_add=improvement_code).run()
            return "Improvement added to 'main.py'."

        elif self.command == "/list agencies/":
            # List all created agencies
            agencies = ", ".join(self.development_agencies.keys())
            return f"Agencies created: {agencies}"

        else:
            return "Unknown command."
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
    
