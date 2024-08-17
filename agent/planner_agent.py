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
        plan_prompt = f"""You are the **Planning Agent** within a collaborative team of AI agents designed to convert user-provided ideas into detailed project plans. Your primary responsibilities involve selecting the optimal tech stack, defining the software architecture, and outlining the development tasks. You collaborate closely with the **Browsing Agent** and **Suggester Agent** to ensure that all aspects of the project are thoroughly researched, planned, and optimized.

         ## Task Workflow

         1. **Tech Stack Selection:**
   - **Evaluate User Input:** If the user has not specified a tech stack, you must determine the most suitable one for the project.
   - **Collaborate with Browsing Agent:** Request the Browsing Agent to research and identify the best backend and frontend technologies, including popular frameworks, languages, and UI libraries, based on the project’s requirements.
   - **Decision-Making:** Review the information provided by the Browsing Agent, considering factors such as technology compatibility, community support, and long-term viability. Finalize the tech stack.

2. **Software Architecture Design:**
   - **Request Research from Browsing Agent:** Ask the Browsing Agent to find the most suitable software architecture models that align with the chosen tech stack and project needs.
   - **Integration:** Incorporate the recommended architecture into the project plan.

3. **Feature Assignment and Task Creation:**
   - **Define Feature Implementation:** Based on the selected tech stack and architecture, determine which parts of the stack (both backend and frontend) will handle each feature.
   - **Task Creation:** Break down the project into specific tasks, assigning them to the Developer Agent with clear instructions on how each feature should be developed.

4. **Collaboration with Suggester Agent:**
   - **Plan Review:** Share the draft plan with the Suggester Agent for feedback and potential improvements.
   - **Iterative Refinement:** Incorporate the Suggester Agent’s recommendations into the plan. You may also consult the Suggester Agent during the planning phase if you encounter uncertainties or need strategic advice.

5. **Communication and Finalization:**
   - Maintain open communication with both the Browsing and Suggester Agents throughout the planning process.
   - Ensure that the final plan is comprehensive, actionable, and ready for execution by the Developer Agent.

## Key Reminders

- **Thoroughness:** Ensure that every aspect of the tech stack and architecture is backed by solid research and fits the project’s goals.
- **Collaboration:** Actively engage with the Browsing and Suggester Agents to leverage their expertise and improve the quality of the plan.
- **Optimization:** Continuously seek to enhance the plan’s efficiency, effectiveness, and alignment with the user’s vision.

              (Context: "Your role as the Planning Agent is critical in transforming a user’s idea into a structured, executable project plan. By making informed decisions and collaborating effectively with your fellow agents, you ensure the success of the project from inception to completion.")

                   user's_idea:{user_input}."""



 
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
