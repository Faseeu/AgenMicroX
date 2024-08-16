# agents/suggester_agent.py
from agency_swarm.agents import Agent
from agency_swarm.tools import BaseTool
from litellm import completion
import json

class SuggesterAgent(Agent):
    def __init__(self, name="Suggester", description="Suggests improvements to the project plan"):
        super().__init__(name, description)

    async def review_plan(self, plan):
        review_prompt = f"Review the following project plan and suggest improvements: {json.dumps(plan)}"
        review_response = await completion(model="groq/llama-3.1-70b-versatile",messages=[{"role": "user", "content": review_prompt}])
        suggestions = json.loads(review_response['choices'][0]['message']['content'])
        
        return json.dumps({"suggestions": suggestions})

    async def get_additional_info(self, query):
        # Communicate with BrowsingAgent to get additional information
        browsing_input = json.dumps({"action": "get_info", "query": query})
        browsing_response = await self.communicate("BrowsingAgent", browsing_input)
        return browsing_response

    async def run(self, input_data):
        input_json = json.loads(input_data)
        action = input_json.get('action')

        if action == 'review_plan':
            return await self.review_plan(input_json['plan'])
        elif action == 'get_info':
            return await self.get_additional_info(input_json['query'])
        else:
            return json.dumps({"error": "Invalid action"})
