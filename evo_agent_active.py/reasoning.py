import json
import re
from typing import Any, Callable


class ReActLoop:
    def __init__(self, llm_client=None, tools: dict[str, Callable] | None = None):
        self.llm = llm_client
        self.tools = tools or {}
        self.max_iterations = 10
        self.history: list[dict[str, str]] = []

    def register_tool(self, name: str, func: Callable):
        self.tools[name] = func

    def run(self, user_input: str) -> str:
        self.history.append({"role": "user", "content": user_input})
        final_answer = None

        for _ in range(self.max_iterations):
            response = self._get_llm_response()
            thought, action = self._parse_react_response(response)

            if thought:
                self.history.append({"role": "assistant", "content": f"Thought: {thought}"})

            if action is None:
                final_answer = response
                break

            action_name, action_input = action
            observation = self._execute_tool(action_name, action_input)
            self.history.append({
                "role": "assistant",
                "content": f"Action: {action_name}({action_input})"
            })
            self.history.append({"role": "system", "content": f"Observation: {observation}"})

        if final_answer is None:
            final_answer = self._get_llm_response()
            self.history.append({"role": "assistant", "content": final_answer})

        return final_answer

    def _get_llm_response(self) -> str:
        if self.llm is None:
            return "Final Answer: No LLM client configured."
        return self.llm.chat(self.history)

    def _parse_react_response(self, response: str) -> tuple[str | None, tuple[str, str] | None]:
        thought_match = re.search(r"Thought:\s*(.+?)(?=\n(?:Action|Final)|\Z)", response, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None

        action_match = re.search(r"Action:\s*(\w+)\((.+?)\)", response, re.DOTALL)
        if action_match:
            action = (action_match.group(1).strip(), action_match.group(2).strip())
            return thought, action

        return thought, None

    def _execute_tool(self, name: str, input_str: str) -> str:
        if name not in self.tools:
            return f"Error: tool '{name}' not found. Available: {list(self.tools.keys())}"

        try:
            args = json.loads(input_str) if input_str.strip().startswith("{") else input_str.strip().strip("'\"")
            return str(self.tools[name](args))
        except Exception as e:
            return f"Error executing {name}: {e}"
