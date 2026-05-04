#!/usr/bin/env python3
"""
Git提交技能 - 提供智能化的Git提交功能

功能:
1. 自动生成规范的commit message
2. 支持常规提交和紧急修复提交
3. 自动识别修改的文件类型
"""

import subprocess
import os
from datetime import datetime
from typing import Optional, List, Tuple


class GitSkill:
    """Git提交技能类，封装Git操作"""
    
    def __init__(self):
        self.repo_path = os.getcwd()
        self.commit_types = {
            'feat': '新功能',
            'fix': '修复bug',
            'docs': '文档更新',
            'style': '代码格式调整',
            'refactor': '代码重构',
            'test': '测试相关',
            'chore': '构建/工具链更新',
            'perf': '性能优化',
            'ci': 'CI/CD配置更新',
            'revert': '回滚'
        }
    
    def run_git_command(self, command: List[str]) -> Tuple[bool, str]:
        """执行Git命令
        
        Args:
            command: Git命令列表，如 ['add', '.']
            
        Returns:
            (success, output) 元组
        """
        try:
            result = subprocess.run(
                ['git'] + command,
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except FileNotFoundError:
            return False, "Git未安装或不在PATH中"
        except Exception as e:
            return False, f"执行Git命令时出错: {str(e)}"
    
    def get_git_status(self) -> str:
        """获取Git仓库当前状态"""
        success, output = self.run_git_command(['status'])
        return output if success else f"获取状态失败: {output}"
    
    def get_staged_files(self) -> List[str]:
        """获取已暂存的文件列表"""
        success, output = self.run_git_command(['diff', '--cached', '--name-only'])
        if success:
            return [f.strip() for f in output.split('\n') if f.strip()]
        return []
    
    def get_modified_files(self) -> List[str]:
        """获取已修改但未暂存的文件列表"""
        success, output = self.run_git_command(['diff', '--name-only'])
        if success:
            return [f.strip() for f in output.split('\n') if f.strip()]
        return []
    
    def get_untracked_files(self) -> List[str]:
        """获取未跟踪的文件列表"""
        success, output = self.run_git_command(['ls-files', '--others', '--exclude-standard'])
        if success:
            return [f.strip() for f in output.split('\n') if f.strip()]
        return []
    
    def get_diff_summary(self) -> str:
        """获取变更摘要"""
        success, output = self.run_git_command(['diff', '--stat'])
        if success:
            return output
        return "无法获取变更摘要"
    
    def classify_changes(self) -> str:
        """智能分类变更类型"""
        files = self.get_staged_files()
        if not files:
            files = self.get_modified_files() + self.get_untracked_files()
        
        if not files:
            return 'chore'
        
        # 根据文件类型和内容判断变更类型
        all_files_str = ' '.join(files).lower()
        
        if any(f.startswith('test') or 'test_' in f for f in files):
            return 'test'
        if any(f.endswith('.md') or 'doc' in f for f in files):
            return 'docs'
        if any('ci' in f or '.yml' in f or '.yaml' in f for f in files):
            return 'ci'
        if 'bug' in all_files_str or 'fix' in all_files_str:
            return 'fix'
        if 'refactor' in all_files_str or '重构' in all_files_str:
            return 'refactor'
        if 'perf' in all_files_str or 'optimize' in all_files_str or '性能' in all_files_str:
            return 'perf'
        
        return 'feat'  # 默认视为新功能
    
    def auto_stage_all(self) -> Tuple[bool, str]:
        """自动暂存所有变更"""
        return self.run_git_command(['add', '-A'])
    
    def create_commit(self, message: str) -> Tuple[bool, str]:
        """创建提交
        
        Args:
            message: 提交信息
            
        Returns:
            (success, output) 元组
        """
        return self.run_git_command(['commit', '-m', message])
    
    def generate_commit_message(self, custom_type: Optional[str] = None) -> str:
        """自动生成规范的commit message
        
        Args:
            custom_type: 自定义提交类型，如 'feat', 'fix' 等
            
        Returns:
            格式化的commit message
        """
        staged = self.get_staged_files()
        modified = self.get_modified_files()
        untracked = self.get_untracked_files()
        
        # 确定变更类型
        commit_type = custom_type or self.classify_changes()
        type_label = self.commit_types.get(commit_type, commit_type)
        
        # 收集变更文件信息
        all_changed = staged + modified + untracked
        
        # 生成描述
        if len(all_changed) == 1:
            description = f"更新 {all_changed[0]}"
        elif len(all_changed) <= 3:
            description = f"更新 {', '.join(all_changed)}"
        else:
            description = f"更新 {len(all_changed)} 个文件"
        
        # 生成完整commit message
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        message = f"{commit_type}: {description}"
        
        # 添加详细文件列表（如果文件较多）
        if len(all_changed) > 3:
            message += "\n\n"
            message += "变更的文件:\n"
            for f in all_changed[:10]:  # 最多显示10个文件
                message += f"- {f}\n"
            if len(all_changed) > 10:
                message += f"... 及其他 {len(all_changed) - 10} 个文件\n"
        
        message += f"\n\n自动提交于 {timestamp}"
        
        return message
    
    def smart_commit(self, message: Optional[str] = None, auto_add: bool = True) -> str:
        """智能提交 - 一键完成暂存和提交
        
        Args:
            message: 自定义提交信息，如果为None则自动生成
            auto_add: 是否自动暂存所有变更
            
        Returns:
            提交结果描述
        """
        # 检查是否是Git仓库
        success, _ = self.run_git_command(['rev-parse', '--git-dir'])
        if not success:
            return "❌ 当前目录不是Git仓库"
        
        # 获取当前状态
        status = self.get_git_status()
        
        # 检查是否有变更
        modified = self.get_modified_files()
        untracked = self.get_untracked_files()
        staged = self.get_staged_files()
        
        if not modified and not untracked and not staged:
            return "✅ 没有需要提交的变更"
        
        # 自动暂存
        if auto_add and (modified or untracked):
            success, output = self.auto_stage_all()
            if not success:
                return f"❌ 暂存失败: {output}"
        
        # 如果没有暂存的文件但有修改的文件
        staged = self.get_staged_files()
        if not staged:
            return "⚠️ 没有暂存的文件，使用 auto_add=True 自动暂存"
        
        # 生成或使用提供的提交信息
        commit_msg = message if message else self.generate_commit_message()
        
        # 执行提交
        success, output = self.create_commit(commit_msg)
        
        if success:
            # 获取提交信息
            _, commit_info = self.run_git_command(['log', '--oneline', '-1'])
            
            result = f"✅ 提交成功!\n"
            result += f"📝 提交信息: {commit_msg.split(chr(10))[0]}\n"
            if commit_info:
                result += f"🔖 提交记录: {commit_info.strip()}\n"
            result += f"📂 涉及 {len(staged)} 个文件"
            return result
        else:
            return f"❌ 提交失败: {output}"
    
    def get_commit_history(self, count: int = 10) -> str:
        """获取提交历史
        
        Args:
            count: 获取的提交数量
            
        Returns:
            格式化的提交历史
        """
        success, output = self.run_git_command([
            'log', f'--max-count={count}',
            '--pretty=format:%h %s (%cr)'
        ])
        
        if success:
            if output:
                return f"📜 最近 {count} 条提交:\n\n{output}"
            else:
                return "📜 暂无提交记录"
        else:
            return f"❌ 获取提交历史失败: {output}"
    
    def create_emergency_commit(self, message: str = "紧急修复") -> str:
        """创建紧急修复提交
        
        Args:
            message: 提交信息
            
        Returns:
            提交结果
        """
        # 强制暂存所有变更
        success, output = self.auto_stage_all()
        if not success:
            return f"❌ 暂存失败: {output}"
        
        # 使用紧急提交信息
        commit_msg = f"fix: {message} [紧急提交]"
        
        success, output = self.create_commit(commit_msg)
        
        if success:
            _, commit_info = self.run_git_command(['log', '--oneline', '-1'])
            return f"🚨 紧急提交成功!\n🔖 {commit_info.strip() if commit_info else ''}\n📝 {commit_msg}"
        else:
            return f"❌ 紧急提交失败: {output}"


# 便捷函数
def git_commit(message: Optional[str] = None) -> str:
    """快速提交函数
    
    Args:
        message: 自定义提交信息
        
    Returns:
        提交结果
    """
    skill = GitSkill()
    return skill.smart_commit(message)


def git_status() -> str:
    """快速查看Git状态"""
    skill = GitSkill()
    return skill.get_git_status()


def git_history(count: int = 10) -> str:
    """快速查看提交历史"""
    skill = GitSkill()
    return skill.get_commit_history(count)


def git_emergency(message: str = "紧急修复") -> str:
    """快速紧急提交"""
    skill = GitSkill()
    return skill.create_emergency_commit(message)
