
import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import shutil
import asyncio

# Add source directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sources.agents import CasualAgent, CoderAgent, FileAgent, PlannerAgent, BrowserAgent
from sources.schemas import executorResult

class MockProvider:
    def __init__(self):
        self.provider_name = "mock"
        self.model = "mock-model"
    
    def get_model_name(self):
        return self.model
    
    def respond(self, history, verbose=True):
        # Convert history to string if it's not already
        if hasattr(history, 'memory') and isinstance(history.memory, list):
             # Extract content from memory
             prompt = "\n".join([str(m.get('content', '')) for m in history.memory])
        else:
             prompt = str(history)
        
        return self.generate(prompt)

    def generate(self, prompt, max_tokens=100, temperature=0.7):
        # Return different responses based on prompt content to simulate agent behavior
        if "casual" in prompt.lower():
            return "Hello! I am the Casual Agent."
        elif "code" in prompt.lower():
            return "Here is some code:\n```python\nprint('Hello')\n```"
        elif "file" in prompt.lower():
            return "I have read the file."
        elif "browser" in prompt.lower() or "search" in prompt.lower():
            return "I have searched the web."
        elif "plan" in prompt.lower():
            return '```json\n[{"task": "Step one", "agent": "casual"}, {"task": "Step two", "agent": "casual"}]\n```'
        return "Generic response."

class TestAgents(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.provider = MockProvider()
        self.prompt_path = os.path.abspath("prompts/base/casual_agent.txt")
        # Ensure prompt file exists or mock it
        if not os.path.exists(self.prompt_path):
            os.makedirs(os.path.dirname(self.prompt_path), exist_ok=True)
            with open(self.prompt_path, "w") as f:
                f.write("You are an agent.")

    async def test_casual_agent(self):
        print("\nTesting CasualAgent...")
        agent = CasualAgent("Casual", self.prompt_path, self.provider)
        response, reasoning = await agent.process("Hello casual agent", None)
        print(f"Response: {response}")
        self.assertIn("Casual Agent", response)

    async def test_coder_agent(self):
        print("\nTesting CoderAgent...")
        # Mocking file operations for CoderAgent might be needed if it tries to read/write
        agent = CoderAgent("Coder", self.prompt_path, self.provider)
        # Coder agent usually expects a request to write code
        # We need to mock the LLM response to include a code block if the agent parses it
        with patch.object(self.provider, 'generate', return_value="Here is code:\n```python\nprint('test')\n```"):
            response, reasoning = await agent.process("Write some code", None)
            print(f"Response: {response}")
            self.assertTrue("code" in response.lower() or "```" in response)

    async def test_file_agent(self):
        print("\nTesting FileAgent...")
        agent = FileAgent("File", self.prompt_path, self.provider)
        # FileAgent needs tools to be mocked if we want to avoid actual FS operations
        # But let's see if basic processing works
        with patch.object(self.provider, 'generate', return_value="I will read the file."):
            response, reasoning = await agent.process("Read file.txt", None)
            print(f"Response: {response}")
            self.assertIsNotNone(response)

    async def test_browser_agent(self):
        print("\nTesting BrowserAgent...")
        # Mock the browser object
        mock_browser = MagicMock()
        mock_browser.get_text.return_value = "Page content"
        
        agent = BrowserAgent("Browser", self.prompt_path, self.provider, browser=mock_browser)
        
        # Mock web_search tool
        mock_search = MagicMock()
        mock_search.execute.return_value = "Search results"
        mock_search.execution_failure_check.return_value = False # Success
        mock_search.interpreter_feedback.return_value = "Search successful"
        
        agent.tools = {"web_search": mock_search}
        
        # We need the LLM to decide to use the search tool if the agent logic relies on LLM output to call tools
        # OR if the agent calls tools hardcoded. 
        # BrowserAgent typically calls search if the prompt implies it, or if the LLM says so.
        # Let's check BrowserAgent implementation. It usually calls web_search directly if it's the first step.
        
        # Actually BrowserAgent.process calls web_search.execute([user_prompt], False)
        
        with patch.object(self.provider, 'generate', return_value="I found this info."):
            response, reasoning = await agent.process("search for apples", None)
            print(f"Response: {response}")
            
            # Verify search was called
            mock_search.execute.assert_called()
            
            # Verify results are in blocks
            has_search_block = any(b.tool_type == "web_search" for b in agent.blocks_result)
            self.assertTrue(has_search_block, "BrowserAgent should create a web_search block")

    async def test_planner_agent(self):
        print("\nTesting PlannerAgent...")
        agent = PlannerAgent("Planner", self.prompt_path, self.provider)
        json_plan = '```json\n{"plan": [{"id": "1", "task": "Step one", "agent": "casual"}, {"id": "2", "task": "Step two", "agent": "casual"}]}\n```'
        with patch.object(self.provider, 'generate', return_value=json_plan):
            response, reasoning = await agent.process("Make a plan", None)
            print(f"Response: {response}")
            self.assertIsNotNone(response)

if __name__ == '__main__':
    unittest.main()
