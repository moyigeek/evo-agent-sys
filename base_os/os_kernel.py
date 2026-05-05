import datetime
import json
import os
import shutil
import subprocess
import sys
import time


def _get_project_root() -> str:
    if getattr(sys, "frozen", False):
        # PyInstaller --onefile: binary at project root
        bin_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        if os.path.basename(bin_dir) == "base_os":
            return os.path.dirname(bin_dir)
        return bin_dir
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(base_dir) == "base_os":
        return os.path.dirname(base_dir)
    return base_dir


PROJECT_ROOT = _get_project_root()


def _load_dotenv():
    env_file = os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(env_file):
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())



_load_dotenv()


class BaseOSKernel:
    def __init__(self):
        self.active_dir = os.path.join(PROJECT_ROOT, "evo_agent_active")
        self.staging_dir = os.path.join(PROJECT_ROOT, "staging_area")
        self.history_dir = os.path.join(PROJECT_ROOT, "history_versions")
        self.entry_point = "main.py"
        self.version = 1.0
        self.crash_log = []
        self.CRASH_WINDOW_SECONDS = 600
        self.MAX_CRASHES = 3

    def run_system(self):
        while True:
            print(f"[Base-OS] 启动 Evo Agent (版本: v{self.version})...")
            process = subprocess.Popen(
                ["python", os.path.join(self.active_dir, self.entry_point)]
            )
            process.wait()

            exit_code = process.returncode

            if exit_code == 42:
                print("[Base-OS] 收到 Evo Agent 的核心升级请求！")
                self.crash_log.clear()
                self.perform_upgrade()
            elif exit_code != 0:
                print(f"[Base-OS] 警告: Evo Agent 崩溃 (退出码 {exit_code})！")
                self.handle_crash(exit_code)
            else:
                print("[Base-OS] Evo Agent 正常关机。")
                break

    def handle_crash(self, exit_code: int):
        now = time.time()
        self.crash_log.append(now)

        self.crash_log = [
            t for t in self.crash_log if now - t <= self.CRASH_WINDOW_SECONDS
        ]

        crash_count = len(self.crash_log)
        window_min = int(self.CRASH_WINDOW_SECONDS / 60)
        print(
            f"[Base-OS] 最近 {window_min} 分钟内崩溃 {crash_count} 次 (上限 {self.MAX_CRASHES})"
        )

        if crash_count >= self.MAX_CRASHES:
            self.perform_rollback(exit_code)
            self.crash_log.clear()
        else:
            print("[Base-OS] 尝试重启...")
            time.sleep(2)

    def perform_rollback(self, crash_exit_code: int):
        print("[Base-OS] 检测到死亡螺旋！正在回滚到上一个稳定版本...")

        backup_versions = []
        if os.path.exists(self.history_dir):
            for entry in os.listdir(self.history_dir):
                entry_path = os.path.join(self.history_dir, entry)
                if os.path.isdir(entry_path) and entry.startswith("v"):
                    backup_versions.append((entry, entry_path))

        if not backup_versions:
            print("[Base-OS] 错误: history_versions 中无可用备份，无法回滚！")
            return

        backup_versions.sort(key=lambda x: x[0], reverse=True)
        latest_backup_name, latest_backup_path = backup_versions[0]

        if os.path.exists(self.active_dir):
            shutil.rmtree(self.active_dir)
        shutil.copytree(latest_backup_path, self.active_dir)
        print(f"[Base-OS] 已从 {latest_backup_name} 回滚")

        recovery_msg = {
            "message": (
                f"你刚才写的代码导致了系统致命崩溃（退出码 {crash_exit_code}），"
                f"已被从 {latest_backup_name} 回滚。"
                f"崩溃时间: {datetime.datetime.now().isoformat()}。"
                f"请分析并修复问题后再尝试升级。"
            )
        }
        recovery_file = os.path.join(PROJECT_ROOT, ".evo_recovery_message.json")
        with open(recovery_file, "w", encoding="utf-8") as f:
            json.dump(recovery_msg, f, ensure_ascii=False, indent=2)
        print("[Base-OS] 已向代理注入恢复消息")

    def perform_upgrade(self):
        print("[Base-OS] 正在执行换脑手术...")

        self.version = round(self.version + 0.1, 1)
        backup_path = os.path.join(self.history_dir, f"v{self.version}")
        shutil.copytree(self.active_dir, backup_path, dirs_exist_ok=True)
        print(f"[Base-OS] 原核心已备份至 {backup_path}")

        shutil.copytree(self.staging_dir, self.active_dir, dirs_exist_ok=True)
        print("[Base-OS] 新核心代码已部署。系统即将使用新核心重启。")
        time.sleep(1)


if __name__ == "__main__":
    os_kernel = BaseOSKernel()
    os_kernel.run_system()
