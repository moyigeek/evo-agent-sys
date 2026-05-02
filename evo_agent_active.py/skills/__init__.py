import os
import json
from typing import Any, Callable


class SkillRegistry:
    def __init__(self):
        self.skills: dict[str, Callable] = {}

    def register(self, name: str, func: Callable):
        self.skills[name] = func

    def execute(self, name: str, params: str) -> str:
        if name not in self.skills:
            return f"Error: skill '{name}' not found. Available: {list(self.skills.keys())}"
        try:
            if params.strip().startswith("{"):
                args = json.loads(params)
                return str(self.skills[name](args))
            return str(self.skills[name](params.strip().strip("'\"")))
        except Exception as e:
            return f"Error executing {name}: {e}"

    def list_skills(self) -> list[str]:
        return list(self.skills.keys())


def read_file(path: str) -> str:
    if not os.path.exists(path):
        return f"Error: file not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(params: dict) -> str:
    path = params.get("path", "")
    content = params.get("content", "")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written {len(content)} bytes to {path}"


def run_command(cmd: str) -> str:
    import subprocess
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout or result.stderr or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out (30s)"
    except Exception as e:
        return f"Error: {e}"


default_skills = SkillRegistry()
default_skills.register("read_file", read_file)
default_skills.register("write_file", write_file)
default_skills.register("run_command", run_command)
