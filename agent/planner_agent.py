# agents/planner_agent.py
from agency_swarm.agents import Agent
from agency_swarm.tools import BaseTool
import json
from litellm import completion
class PlannerAgent(Agent):
    def __init__(self, name="Planner", description="Plans the project architecture and tasks"):
        super().__init__(name, description)
        self.plan = {}

    async def create_plan(self, user_input):
        # Generate initial plan based on user input
        plan_prompt = f"Create a detailed project plan based on the following user input: {user_input}"
        plan_response = await completion(model="groq/llama-3.1-70b-versatile", messages=[{"role": "user", "content": plan_prompt}])
        self.plan = json.loads(plan_response['choices'][0]['message']['content'])
        
        # Communicate with SuggesterAgent for improvements
        suggester_input = json.dumps({"action": "review_plan", "plan": self.plan})
        suggester_response = await self.communicate("SuggesterAgent", suggester_input)
        suggester_feedback = json.loads(suggester_response)
        
        # Incorporate suggestions
        self.plan = self.incorporate_suggestions(self.plan, suggester_feedback['suggestions'])
        
        return json.dumps(self.plan)

    async def get_tech_stack(self):
        # Communicate with BrowsingAgent to get tech stack recommendations
        browsing_input = json.dumps({"action": "get_tech_stack", "requirements": self.plan['requirements']})
        browsing_response = await self.communicate("BrowsingAgent", browsing_input)
        tech_stack = json.loads(browsing_response)
        
        self.plan['tech_stack'] = tech_stack
        return json.dumps(tech_stack)

    async def get_architecture(self):
        # Communicate with BrowsingAgent to get architecture recommendations
        browsing_input = json.dumps({"action": "get_architecture", "tech_stack": self.plan['tech_stack']})
        browsing_response = await self.communicate("BrowsingAgent", browsing_input)
        architecture = json.loads(browsing_response)
        
        self.plan['architecture'] = architecture
        return json.dumps(architecture)

    def incorporate_suggestions(self, plan, suggestions):
        # Logic to incorporate suggestions into the plan
        for suggestion in suggestions:
            if suggestion['type'] == 'add':
                plan[suggestion['key']] = suggestion['value']
            elif suggestion['type'] == 'modify':
                plan[suggestion['key']] = suggestion['value']
            elif suggestion['type'] == 'remove':
                plan.pop(suggestion['key'], None)
        return plan

    async def run(self, user_input):
        plan = await self.create_plan(user_input)
        tech_stack = await self.get_tech_stack()
        architecture = await self.get_architecture()
        
        return json.dumps({
            "plan": json.loads(plan),
            "tech_stack": json.loads(tech_stack),
            "architecture": json.loads(architecture)
        })
