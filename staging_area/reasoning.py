import json
import re
from typing import Callable


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
            thought, actions = self._parse_react_response(response)

            if thought:
                self.history.append(
                    {"role": "assistant", "content": f"Thought: {thought}"}
                )

            if not actions:
                final_answer = response
                break

            for action_name, action_input in actions:
                observation = self._execute_tool(action_name, action_input)
                self.history.append(
                    {
                        "role": "assistant",
                        "content": f"Action: {action_name}({action_input})",
                    }
                )
                self.history.append(
                    {"role": "system", "content": f"Observation: {observation}"}
                )

        if final_answer is None:
            final_answer = self._get_llm_response()
            self.history.append({"role": "assistant", "content": final_answer})

        return final_answer

    def _get_llm_response(self) -> str:
        if self.llm is None:
            return "Final Answer: No LLM client configured."
        return self.llm.chat(self.history)

    def _find_matching_paren(self, text: str, start: int) -> int:
        depth = 0
        i = start
        while i < len(text):
            ch = text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return len(text)

    def _find_matching_brace(self, text: str, start: int) -> int:
        depth = 0
        i = start
        while i < len(text):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return len(text)

    def _parse_react_response(
        self, response: str
    ) -> tuple[str | None, list[tuple[str, str]]]:
        thought_match = re.search(
            r"Thought:\s*(.+?)(?=\n(?:Action|Final)|\Z)", response, re.DOTALL
        )
        thought = thought_match.group(1).strip() if thought_match else None

        actions = []
        for m in re.finditer(r"Action:\s*(\w+)\s*\(", response):
            func_name = m.group(1)
            paren_start = m.end() - 1
            paren_end = self._find_matching_paren(response, paren_start)

            if paren_end < len(response):
                params_raw = response[paren_start + 1 : paren_end].strip()
            else:
                params_raw = response[paren_start + 1 :].strip()

            params = self._extract_params(params_raw)
            if params is not None:
                actions.append((func_name, params))

        return thought, actions

    def _extract_params(self, raw: str) -> str | None:
        raw = raw.strip()
        if not raw:
            return raw

        if raw.startswith("{"):
            end = self._find_matching_brace(raw, 0)
            if end < len(raw):
                return raw[: end + 1].strip()

        if raw.startswith('"'):
            end = raw.index('"', 1) if '"' in raw[1:] else len(raw)
            return raw[1:end]

        return raw

    def _execute_tool(self, name: str, input_str: str) -> str:
        if name not in self.tools:
            return (
                f"Error: tool '{name}' not found. Available: {list(self.tools.keys())}"
            )

        try:
            args = (
                json.loads(input_str)
                if input_str.strip().startswith("{")
                else input_str.strip().strip("'\"")
            )
            return str(self.tools[name](args))
        except Exception as e:
            return f"Error executing {name}: {e}"
