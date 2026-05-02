import os
import json
import urllib.request
import urllib.error


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("EVO_LLM_API_KEY", "")
        self.api_base = (api_base or os.environ.get("EVO_LLM_API_BASE", "https://api.openai.com")).rstrip("/")
        self.model = model or os.environ.get("EVO_LLM_MODEL", "gpt-4o")
        self.system_prompt: str | None = None
        self.temperature: float = 0.7
        self.max_tokens: int = 4096

    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt

    def chat(self, messages: list[dict[str, str]]) -> str:
        full_messages = []
        if self.system_prompt:
            full_messages.append({"role": "system", "content": self.system_prompt})
        full_messages.extend(messages)

        url = f"{self.api_base}/v1/chat/completions"
        body = json.dumps({
            "model": self.model,
            "messages": full_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            return f"[LLM Error] HTTP {e.code}: {error_body}"
        except Exception as e:
            return f"[LLM Error] {e}"

    def generate_code(self, task_description: str, existing_code: str = "") -> str:
        messages = [
            {
                "role": "user",
                "content": (
                    f"## 任务\n{task_description}\n\n"
                    f"## 现有代码 (仅供参考)\n```python\n{existing_code}\n```\n\n"
                    f"请仅输出完整的 Python 代码，不要包含任何解释或 markdown 标记。"
                ),
            }
        ]
        return self.chat(messages).strip()
