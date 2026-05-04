import json
import re
from typing import Callable


class ReActLoop:
    def __init__(self, llm_client=None, tools: dict[str, Callable] | None = None):
        self.llm = llm_client
        self.tools = tools or {}
        self.max_iterations = 6  # 从10减少到6，减少不必要的循环
        self.history: list[dict[str, str]] = []
        self._response_cache = {}  # 响应缓存
        self._tool_result_cache = {}  # 工具结果缓存

    def register_tool(self, name: str, func: Callable):
        self.tools[name] = func

    def _get_cache_key(self, user_input: str) -> str:
        """生成缓存键"""
        # 只缓存简单的查询，复杂任务不缓存
        if len(user_input) < 100 and not any(c in user_input for c in '{"'):
            return f"{user_input}_{len(self.history)}"
        return None

    def run(self, user_input: str) -> str:
        self.history.append({"role": "user", "content": user_input})
        final_answer = None

        # 快速路径：检查缓存
        cache_key = self._get_cache_key(user_input)
        if cache_key and cache_key in self._response_cache:
            cached = self._response_cache[cache_key]
            self.history.append({"role": "assistant", "content": cached})
            return cached

        for iteration in range(self.max_iterations):
            # 使用优化的prompt，减少token消耗
            response = self._get_llm_response()

            # 快速路径：如果响应很短且包含Final Answer，直接返回
            if "Final Answer:" in response and len(response) < 200:
                final_answer = response
                self.history.append({"role": "assistant", "content": final_answer})
                if cache_key:
                    self._response_cache[cache_key] = final_answer
                return final_answer

            thought, action = self._parse_react_response(response)

            if thought:
                self.history.append(
                    {"role": "assistant", "content": f"Thought: {thought}"}
                )

            if action is None:
                final_answer = response
                break

            action_name, action_input = action
            
            # 工具结果缓存：相同输入的工具调用结果缓存
            tool_cache_key = f"{action_name}:{action_input}"
            if tool_cache_key in self._tool_result_cache:
                observation = self._tool_result_cache[tool_cache_key]
            else:
                observation = self._execute_tool(action_name, action_input)
                # 只缓存文件读取等幂等操作
                if action_name in ["read_file", "run_command"]:
                    self._tool_result_cache[tool_cache_key] = observation

            self.history.append(
                {
                    "role": "assistant",
                    "content": f"Action: {action_name}({action_input})",
                }
            )
            self.history.append(
                {"role": "system", "content": f"Observation: {observation}"}
            )

            # 提前终止：如果观察到错误，尝试直接给出答案
            if observation.startswith("Error:"):
                # 尝试直接回答而不是继续循环
                final_response = self._get_llm_response()
                if "Final Answer:" in final_response:
                    final_answer = final_response
                    break

        if final_answer is None:
            final_answer = self._get_llm_response()
            self.history.append({"role": "assistant", "content": final_answer})

        # 缓存结果
        if cache_key:
            self._response_cache[cache_key] = final_answer

        return final_answer

    def _get_llm_response(self) -> str:
        if self.llm is None:
            return "Final Answer: No LLM client configured."
        return self.llm.chat(self.history)

    def _parse_react_response(
        self, response: str
    ) -> tuple[str | None, tuple[str, str] | None]:
        thought_match = re.search(
            r"Thought:\s*(.+?)(?=\n(?:Action|Final)|\Z)", response, re.DOTALL
        )
        thought = thought_match.group(1).strip() if thought_match else None

        # Try format: Action: name(...)
        action_match = re.search(r"Action:\s*(\w+)\((.+?)\)\s*$", response, re.DOTALL)
        if action_match:
            action = (action_match.group(1).strip(), action_match.group(2).strip())
            return thought, action

        # Try format: Action: name\n{json_body} (multi-line variant)
        action_match = re.search(
            r"Action:\s*(\w+)\s*\n\s*(\{.*?\})\s*$", response, re.DOTALL
        )
        if action_match:
            action = (action_match.group(1).strip(), action_match.group(2).strip())
            return thought, action

        return thought, None

    def _execute_tool(self, name: str, input_str: str) -> str:
        if name not in self.tools:
            return (
                f"Error: tool '{name}' not found. Available: {list(self.tools.keys())}"
            )

        try:
            args = (
                json.loads(input_str)
                if input_str.strip().startswith("{")
                else input_str.strip().strip("\"'")
            )
            return str(self.tools[name](args))
        except Exception as e:
            return f"Error executing {name}: {e}"
