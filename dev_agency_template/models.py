from pydantic import BaseModel
from typing import List, Dict

class Task(BaseModel):
    task_id: str
    description: str
    functions: List[str]
    details: Dict[str, str]

class CodeFile(BaseModel):
    file_name: str
    code: str
    task_id: str

class Plan(BaseModel):
    project_name: str
    tasks: List[Task]

class CodeSubmission(BaseModel):
    project_name: str
    files: List[CodeFile]
  
