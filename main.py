# main.py
from config.config import GROQ_API_KEY
import json
from agency_swarm import Agency, set_openai_key
from agent.planner_agent import PlannerAgent
from agent.suggester_agent import SuggesterAgent
from agent.browsing_agent import BrowsingAgent
import os
from openai import OpenAI
from astra_assistants import patch


def main():
    # Set the OpenAI key
    client = patch(OpenAI())
    set_openai_client(client)

    # Initialize agents
    planner = PlannerAgent()
    suggester = SuggesterAgent()
    browser = BrowsingAgent()

    # Initialize the agency with the agent communication chart
    agency = Agency(
        agency_chart=[senior_developer, #Top level agent
            [senior_developer, planner],       
            [planner, suggester],   # Communication between planner and suggester
            [planner, browser],     # Communication between planner and browser
            [suggester, browser]    # Communication between suggester and browser
        ],
        temperature=0.5
        max_prompt_tokens=15000
    )
    


    # Get user input
    user_input = input("Please provide your query: ")

    # Run the agency to handle the input
    planner_result = agency.get_completion(user_input, recipient_agent=planner)
    print("Planner agent result:", planner_result)

    # Optionally, interact with specific agents like the browser
    browser_input = json.dumps({"query": user_input, "chat_history": []})
    browser_result = agency.get_completion(browser_input, recipient_agent=browser)
    print("Browsing agent result:", browser_result)

if __name__ == "__main__":
    main()
    
