# main.py
from agency_swarm import Agency
from agent.planner_agent import PlannerAgent
from agent.suggester_agent import SuggesterAgent
from agent.browsing_agent import BrowsingAgent
from config.config import GROQ_API_KEY, GROQ_API_BASE
import asyncio
import json

async def main():
    # Initialize the agency
    agency = Agency(openai_api_key=GROQ_API_KEY, openai_api_base=GROQ_API_BASE)

    # Create agents
    planner = PlannerAgent()
    suggester = SuggesterAgent()
    browser = BrowsingAgent()

    # Add agents to the agency
    agency.add_agent(planner)
    agency.add_agent(suggester)
    agency.add_agent(browser)

    # Set up communication channels
    agency.add_communication_channel(planner, suggester)
    agency.add_communication_channel(planner, browser)
    agency.add_communication_channel(suggester, browser)

    # Get user input
    user_input = input("Please provide your query: ")

    # Run the browsing agent
    browser_input = json.dumps({"query": user_input, "chat_history": []})
    result = await browser.run(browser_input)
    print("Browsing agent result:", result)

    # Run the planner agent
    planner_result = await planner.run(user_input)
    print("Planner agent result:", planner_result)

if __name__ == "__main__":
    asyncio.run(main())
