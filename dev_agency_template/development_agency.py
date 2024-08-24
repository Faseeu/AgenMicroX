from models import Plan, CodeSubmission, Task, CodeFile

class ExpertDeveloperAgent:
    def __init__(self):
      self.modal="groq/llama-3.1-70b-versatile"
      self.instructions=""
      self.memory = {}

    def work_on_task(self, task: Task) -> CodeFile:
        generated_code = f"# Code for {task.description}\ndef {task.functions[0]}():\n    pass"
        return CodeFile(
            file_name=f"{task.task_id}.py",
            code=generated_code,
            task_id=task.task_id
        )

class VerifierAgent:
    def __init__(self):
        self.modal="groq/llama-3.1-70b-versatile"
        self.instructions=""
        self.memory = {}

    def verify_code(self, plan_json, code_json):
        pass

    def verify_and_finalize_code(self, code_submission: CodeSubmission) -> bool:
        for file in code_submission.files:
            task = next((t for t in plan.tasks if t.task_id == file.task_id), None)
            if task:
                if f"# Code for {task.description}" not in file.code:
                    return False
        return True

class DevelopmentAgency:
    def __init__(self, verifier_agent, developer_agents):
        self.verifier_agent = verifier_agent
        self.developer_agents = developer_agents
        self.plan = None

    def receive_plan(self, plan_json: str):
        self.plan = Plan.parse_raw(plan_json)
        for developer in self.developer_agents:
            for task in self.plan.tasks:
                developer.memory['current_task'] = task
                break

    def collect_code(self) -> CodeSubmission:
        submitted_files = []
        for developer in self.developer_agents:
            task = developer.memory.get('current_task')
            if task:
                code_file = developer.work_on_task(task)
                submitted_files.append(code_file)
        return CodeSubmission(
            project_name=self.plan.project_name,
            files=submitted_files
        )

    def handle_message(self, message: str):
        # Process a message sent from the Senior Developer Agent
        pass

    def verify_and_finalize_code(self, code_submission: CodeSubmission) -> bool:
        return self.verifier_agent.verify_and_finalize_code(code_submission)
      
