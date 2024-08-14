# agents/browsing_agent.py
import json
import asyncio
from typing import List, Dict, Any, Optional
from agency_swarm.agents import Agent
from agency_swarm.tools import BaseTool
from agency_swarm.util.oai import chat_completion_request
from config.config import GROQ_API_KEY, GROQ_API_BASE, SEARXNG_INSTANCE
import aiohttp
from bs4 import BeautifulSoup
import re
from datetime import datetime
from urllib.parse import urlencode
import yaml
from pathlib import Path
class SearxngSearchOptions:
    def __init__(self, categories: Optional[List[str]] = None, 
                 engines: Optional[List[str]] = None, 
                 language: Optional[str] = None, 
                 pageno: Optional[int] = None):
        self.categories = categories
        self.engines = engines
        self.language = language
        self.pageno = pageno

class SearxngSearchResult:
    def __init__(self, title: str, url: str, img_src: Optional[str] = None, 
                 thumbnail_src: Optional[str] = None, thumbnail: Optional[str] = None, 
                 content: Optional[str] = None, author: Optional[str] = None, 
                 iframe_src: Optional[str] = None):
        self.title = title
        self.url = url
        self.img_src = img_src
        self.thumbnail_src = thumbnail_src
        self.thumbnail = thumbnail
        self.content = content
        self.author = author
        self.iframe_src = iframe_src

class BrowsingAgent(Agent):
    def __init__(self, name="Browsing", description="Advanced AI browsing agent"):
        super().__init__(name, description)
        # Load the settings.yml file
        settings = Path(__file__).resolve().parent.parent / "config" / "settings.yml"
        with open(settings_path, 'r') as file:
           self.settings = yaml.safe_load(file)

        self.searxng_instance = config_data.get('searxng_instance', SEARXNG_INSTANCE)
        self.groq_model = config_data.get('groq_model', "mixtral-8x7b-32768")  # Use default if not in settings.yml
       
     
        # You can change this to your preferred model

    async def search_searxng(self, query: str, opts: Optional[SearxngSearchOptions] = None) -> Dict[str, Any]:
        url = f"{self.searxng_instance}/search"
        params = {
            "q": query,
            "format": "json"
        }

        if opts:
            if opts.categories:
                params["categories"] = ",".join(opts.categories)
            if opts.engines:
                params["engines"] = ",".join(opts.engines)
            if opts.language:
                params["language"] = opts.language
            if opts.pageno:
                params["pageno"] = str(opts.pageno)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

                results = [SearxngSearchResult(**result) for result in data.get("results", [])]
                suggestions = data.get("suggestions", [])

                return {"results": results, "suggestions": suggestions}
               )
    async def refined_search_retriever(self, query: str, chat_history: List[Dict[str, str]]) -> str:
        prompt = f"""
        You are Perplexica, an advanced AI browsing agent. Analyze the conversation and follow-up question below. Your task is to:

        1. Rephrase the question for optimal web searching if needed.
        2. Determine if web searching is necessary or if the task requires other tools.
        3. Identify any links provided for analysis.
        4. Recognize if the task is a writing assignment or simple greeting.

        Guidelines:
        - For writing tasks or greetings, return 'not_needed'.
        - If links are provided, return them within a 'links' XML block and the question in a 'question' XML block.
        - For summarization requests, return 'Summarize' as the question in the 'question' XML block.
        - If no links are provided, return the rephrased question without XML blocks.

        Conversation:
        {self.format_chat_history(chat_history)}

        Follow-up question: {query}
        Analyzed and Rephrased Query:
        """
        response = await chat_completion_request(messages=[{"role": "user", "content": prompt}])
        return response['choices'][0]['message']['content']

    async def get_document_from_link(self, link: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator='\n', strip=True)
                return {
                    "pageContent": text,
                    "metadata": {
                        "source": link,
                        "title": soup.title.string if soup.title else "No title"
                    }
                }

    async def verify_content(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        verification_prompt = """
        Analyze the following content for credibility and potential biases:
        
        {content}
        
        Provide a brief assessment of:
        1. The credibility of the source
        2. Any potential biases or limitations
        3. Corroboration with other sources (if applicable)
        
        Assessment:
        """
        
        verified_docs = []
        for doc in docs:
            prompt = verification_prompt.format(content=doc["pageContent"])
            response = await chat_completion_request(messages=[{"role": "user", "content": prompt}])
            doc["metadata"]["credibilityAssessment"] = response['choices'][0]['message']['content']
            verified_docs.append(doc)
        
        return verified_docs

    async def compare_documents(self, docs: List[Dict[str, Any]], query: str) -> str:
        comparison_prompt = f'''
        Compare the following documents in relation to the query: "{query}"
        
        Documents:
        {self.format_documents(docs)}
        
        Provide a comparison highlighting:
        1. Key similarities
        2. Notable differences
        3. Unique insights from each source
        
        Comparison:        
        '''
        
        response = await chat_completion_request(messages=[{"role": "user", "content": comparison_prompt}])
        return response['choices'][0]['message']['content']

    async def process_documents(self, docs: List[Dict[str, Any]], query: str) -> str:
        verified_docs = await self.verify_content(docs)
        comparison_result = await self.compare_documents(verified_docs, query)
        
        processed_content = "\n\n".join([
            f"{i+1}. {doc['pageContent']}\nCredibility Assessment: {doc['metadata']['credibilityAssessment']}"
            for i, doc in enumerate(verified_docs)
        ])
        
        return f"{processed_content}\n\nComparison Analysis:\n{comparison_result}"

    async def perplexica_agent(self, query: str, chat_history: List[Dict[str, str]]) -> str:
        refined_query = await self.refined_search_retriever(query, chat_history)
        
        if refined_query == 'not_needed':
            return "How can I assist you with your task or writing assignment?"

        links_match = re.search(r'<links>(.*?)</links>', refined_query, re.DOTALL)
        question_match = re.search(r'<question>(.*?)</question>', refined_query, re.DOTALL)

        links = links_match.group(1).split('\n') if links_match else []
        processed_query = question_match.group(1) if question_match else refined_query

        if links:
            docs = await asyncio.gather(*[self.get_document_from_link(link) for link in links])
        else:
            search_results = await self.search_searxng(processed_query, SearxngSearchOptions(language="en"))
            docs = [
                {
                    "pageContent": result.content or "",
                    "metadata": {
                        "title": result.title,
                        "url": result.url,
                        "img_src": result.img_src,
                        "thumbnail": result.thumbnail,
                        "author": result.author
                    }
                }
                for result in search_results["results"]
            ]

        processed_docs = await self.process_documents(docs, processed_query)

        perplexica_prompt = f"""
        You are Perplexica, an advanced AI browsing agent with the following capabilities:

        1. Intelligent Web Searching
        2. Content Summarization
        3. Information Synthesis
        4. Data Extraction and Analysis
        5. Comparative Analysis
        6. Content Verification
        7. Natural Language Interaction
        8. Multilingual Capabilities

        Your task is to provide informative, relevant, and well-structured responses based on the provided context and user query. Follow these guidelines:

        1. Use an unbiased and journalistic tone.
        2. Do not repeat text verbatim from the context.
        3. Provide answers within your response; do not direct users to external links.
        4. Use markdown for formatting, including bullet points for listing information.
        5. Cite your sources using [number] notation at the end of relevant sentences.
        6. If the context is insufficient, state that you couldn't find relevant information and offer to search again or suggest related queries.
        7. For summarization tasks, provide a concise yet comprehensive overview of the main points.
        8. When comparing information, highlight similarities, differences, and potential biases.
        9. If asked about credibility, assess the sources and mention any potential biases or limitations.

        Remember, your goal is to be helpful, accurate, and ethical in your information delivery.

        Context:
        <context>
        {processed_docs}
        </context>

        Today's date is {datetime.now().isoformat()}

        Chat History:
        {self.format_chat_history(chat_history)}

        User Query: {query}

        Response:
        """

        response = await chat_completion_request(messages=[{"role": "user", "content": perplexica_prompt}])
        return response['choices'][0]['message']['content']

    def format_chat_history(self, chat_history: List[Dict[str, str]]) -> str:
        return "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history])

    def format_documents(self, docs: List[Dict[str, Any]]) -> str:
        return "\n\n".join([f"Document {i+1}:\n{doc['pageContent']}" for i, doc in enumerate(docs)])

    async def run(self, input_data: str) -> str:
        input_json = json.loads(input_data)
        query = input_json.get('query')
        chat_history = input_json.get('chat_history', [])

        result = await self.perplexica_agent(query, chat_history)
        return json.dumps({"response": result})
