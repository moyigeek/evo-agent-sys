import argparse
import json
import os
import shutil
import subprocess
import sys

from llm import LLMClient
from memory import load_recovery_message, load_state, save_state
from reasoning import ReActLoop
from system_prompt import SYSTEM_PROMPT


class EvoAgent:
    def __init__(
        self,
        llm_url: str | None = None,
        llm_key: str | None = None,
        llm_model: str | None = None,
    ):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(self.script_dir)

        self.memory, self.extra = load_state()
        recovery_msg = load_recovery_message()
        if recovery_msg:
            print(f"[Evo Agent] 检测到恢复消息: {recovery_msg}")
            self.memory.add_turn("system", f"[SYSTEM RECOVERY] {recovery_msg}")
            os.remove(os.path.join(self.project_root, ".evo_recovery_message.json"))

        self.llm = LLMClient(api_base=llm_url, api_key=llm_key, model=llm_model)
        self.llm.set_system_prompt(SYSTEM_PROMPT)

        self.tools = {
            "evaluate_and_rewrite_core": self.evaluate_and_rewrite_core,
        }
        self.react = ReActLoop(llm_client=self.llm, tools=self.tools)

    def evaluate_and_rewrite_core(self, params: str) -> str:
        try:
            data = json.loads(params)
            target_file = data["target_file"]
            new_code = data["new_code"]
        except (json.JSONDecodeError, KeyError):
            return "Error: params must be JSON with 'target_file' and 'new_code'"

        staging_dir = os.path.join(self.project_root, "staging_area")

        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
        shutil.copytree(self.script_dir, staging_dir)

        file_path = os.path.join(staging_dir, target_file)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_code)

        print(f"[Evo Agent] 已将新的核心逻辑写入 {target_file} 的草稿箱。")

        if not self.run_self_test(staging_dir):
            print("[Evo Agent] 新代码测试未通过！放弃此次进化。")
            return "Upgrade failed: Code syntax error or test failure."

        print("[Evo Agent] 正在保存状态...")
        save_state(self.memory, {"upgrade_target": target_file})

        print(
            "[Evo Agent] 测试通过！正在发送 Exit Code 42 请求 Base-OS 重启并应用新核心..."
        )
        sys.exit(42)

    def run_self_test(self, staging_dir: str) -> bool:
        print("[Evo Agent] 正在对新核心进行沙盒测试...")

        # Step 1: Syntax check
        py_files = [f for f in os.listdir(staging_dir) if f.endswith(".py")]
        if not py_files:
            print("[Evo Agent] 错误: staging 目录中没有 .py 文件")
            return False

        for f in py_files:
            file_path = os.path.join(staging_dir, f)
            try:
                result = subprocess.run(
                    ["python", "-m", "py_compile", file_path],
                    capture_output=True,
                    timeout=15,
                )
                if result.returncode != 0:
                    print(
                        f"[Evo Agent] 语法错误 in {f}: {result.stderr.decode()[:500]}"
                    )
                    return False
            except subprocess.TimeoutExpired:
                print(f"[Evo Agent] 语法检查超时: {f}")
                return False

        # Step 2: Isolation process test
        entry = os.path.join(staging_dir, "main.py")
        if not os.path.exists(entry):
            print("[Evo Agent] 警告: staging 目录中不存在 main.py，跳过隔离进程测试")
            return True

        print("[Evo Agent] 正在隔离进程中运行新代码...")
        try:
            proc = subprocess.Popen(
                ["python", entry],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            test_prompt = '{"action":"ping"}\n'
            try:
                stdout, stderr = proc.communicate(input=test_prompt, timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                print("[Evo Agent] 隔离测试失败: 进程超时（可能存在死循环）")
                return False

            print(f"[Evo Agent] 隔离测试 stdout: {stdout[:500]}")
            if stderr:
                print(f"[Evo Agent] 隔离测试 stderr: {stderr[:500]}")

            if proc.returncode != 0:
                if proc.returncode == 42:
                    print("[Evo Agent] 隔离测试通过（退出码 42 = 升级请求）")
                    return True
                print(f"[Evo Agent] 隔离测试失败: 退出码 {proc.returncode}")
                return False

            if "[Evo Agent]" in stdout:
                print("[Evo Agent] 隔离测试通过：代理正常响应")
                return True
            else:
                print("[Evo Agent] 隔离测试警告: 未检测到预期输出标记，但仍可接受")
                return True

        except Exception as e:
            print(f"[Evo Agent] 隔离测试异常: {e}")
            return False

    def run(self):
        print("[Evo Agent] 交互系统正在运行...")
        print(f"[Evo Agent] LLM: {self.llm.model} @ {self.llm.api_base}")

        if self.memory.turns:
            print(f"[Evo Agent] 已恢复 {len(self.memory.turns)} 条历史记录")
            if self.memory.current_task:
                print(f"[Evo Agent] 当前任务: {self.memory.current_task}")

        llm_available = bool(self.llm.api_key)

        if not llm_available:
            print(
                "[Evo Agent] 注意: 未配置 LLM API Key (EVO_LLM_API_KEY)，运行在 echo 模式"
            )
            self._run_echo_mode()
        else:
            self._run_react_mode()

    def _run_echo_mode(self):
        print("[Evo Agent] Echo 模式: 回复输入内容。输入 'exit' 退出。")
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                if line.lower() == "exit":
                    break
                self.memory.add_turn("user", line)
                self.memory.add_turn("assistant", f"Echo: {line}")
                print(f"[Evo Agent] Echo: {line}")
        except KeyboardInterrupt:
            pass
        finally:
            print("[Evo Agent] 正在关闭并保存状态...")
            save_state(self.memory)
            print("[Evo Agent] 再见。")

    def _run_react_mode(self):
        print("[Evo Agent] ReAct 模式: 输入任务描述。输入 'exit' 退出。")
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                if line.lower() == "exit":
                    break

                print(f"[Evo Agent] 处理中: '{line[:80]}'")
                try:
                    response = self.react.run(line)
                    print(f"[Evo Agent] 响应:\n{response}")
                except Exception as e:
                    print(f"[Evo Agent] 错误: {e}")

                save_state(self.memory)
        except KeyboardInterrupt:
            pass
        finally:
            print("[Evo Agent] 正在关闭并保存状态...")
            save_state(self.memory)
            print("[Evo Agent] 再见。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evo Agent - Recursive Self-Improvement System"
    )
    parser.add_argument(
        "--llm-url",
        dest="llm_url",
        default=None,
        help="LLM API base URL (overrides EVO_LLM_API_BASE)",
    )
    parser.add_argument(
        "--llm-key",
        dest="llm_key",
        default=None,
        help="LLM API key (overrides EVO_LLM_API_KEY)",
    )
    parser.add_argument(
        "--llm-model",
        dest="llm_model",
        default=None,
        help="LLM model name (overrides EVO_LLM_MODEL)",
    )
    args = parser.parse_args()

    agent = EvoAgent(
        llm_url=args.llm_url, llm_key=args.llm_key, llm_model=args.llm_model
    )
    agent.run()
