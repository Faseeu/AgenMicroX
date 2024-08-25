# main.py
from agency_swarm import Agency, set_openai_client
from agent.planner_agent import PlannerAgent
from agent.suggester_agent import SuggesterAgent
from agent.browsing_agent import BrowsingAgent
import os
from openai import OpenAI
from astra_assistants import patch
from agent.senior_developer import SeniorDeveloperAgent

def main():
    # Set the OpenAI key
    client = patch(OpenAI())
    set_openai_client(client)

    # Initialize agents
    planner = PlannerAgent()
    suggester = SuggesterAgent()
    browser = BrowsingAgent()
    senior_developer = SeniorDeveloperAgent()

    # Initialize the agency with the agent communication chart
    planner_agency = Agency(
        agency_chart=[
           # Top-level agent
            planner,       
            [planner, suggester],   # Communication between planner and suggester
            [planner, browser],     # Communication between planner and browser
            [suggester, browser]    # Communication between suggester and browser
        ],
        temperature=0.5,
        max_prompt_tokens=15000
    )
    frontend_dev_agency = Agency(
        agency_chart=[
           # Top-level agent
            verifier,       
            [planner, suggester],   # Communication between planner and suggester
            [planner, browser],     # Communication between planner and browser
            [suggester, browser]    # Communication between suggester and browser
        ],
        temperature=0.5,
        max_prompt_tokens=15000,
        shared_instructions=""
    )
    agency = Agency(
        agency_chart=[
            senior_developer,
            [senior_developer, planner_agency],
            [senior_developer, frontend_dev_agency],
        ]
    )
    while True:
        # Get user input
        user_input = input("Please provide your query or command: ")

        if user_input.startswith("/create agency "):
            try:
                _, agency_name, num_devs = user_input.split(" ")
                result = senior_developer.run_tool("CreateAgencyTool", agency_name=agency_name, num_developers=int(num_devs))
                print(result)
            except ValueError:
                print("Invalid input. Use: /create agency <agency_name> <num_devs>")

        elif user_input.startswith("/assign plan "):
            _, agency_name = user_input.split(" ", 2)
            # Example plan provided directly for simplicity
            plan = {
                "project_name": "Example Project",
                "tasks": [
                    {"task_id": "1", "description": "Create example feature", "functions": ["example_function"], "details": {}}
                ]
            }
            result = senior_developer.run_tool("AssignPlanToAgencyTool", agency_name=agency_name, plan=edited_plan)
            print(result)

        elif user_input.startswith("/implement code "):
            _, agency_name = user_input.split(" ", 2)
            result = senior_developer.run_tool("ImplementCodeTool", agency_name=agency_name)
            print(result)

        elif user_input.startswith("/add functionality/") or user_input.startswith("/add improvement/"):
            result = senior_developer.run_tool("HandleTerminalCommandTool", command=user_input)
            print(result)

        elif user_input == "/list agencies/":
            result = senior_developer.run_tool("HandleTerminalCommandTool", command=user_input)
            print(result)

        elif user_input == "exit":
            print("Exiting...")
            break
        elif user_input == "/search/":
            # Optionally, interact with specific agents like the browser
            browser_input = json.dumps({"query": user_input, "chat_history": []})
            browser_result = agency.get_completion(browser_input, recipient_agent=browser)
            print("Browsing agent result:", browser_result)
            
        else:
            # Run the agency to handle the input as a general query
            planner_result = planner_agency.get_completion(user_input, recipient_agent=planner)
            print("Planner agent result:", planner_result)

            plan_to_code = agency.get_completion(planner_result, recipient_agent=senior_developer)
            plan_for_devs = json.dumps({"plan_for_frontend":[], "plan_for_backend":[])
            
if __name__ == "__main__":
    main()
            
