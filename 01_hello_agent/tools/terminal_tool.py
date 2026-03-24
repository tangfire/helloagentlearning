"""
TerminalTool - 终端工具

用于执行 shell 命令，探索代码库结构。
支持安全的命令执行、输出捕获和错误处理。
"""

import subprocess
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import hashlib


class TerminalTool:
    """
    终端工具
    
    核心功能：
    1. 安全执行 shell 命令
    2. 探索代码库结构（ls, find, tree 等）
    3. 查看文件内容（cat, head, tail 等）
    4. 代码分析（wc, grep 等）
    5. Git 操作支持
    """
    
    def __init__(self, working_dir: Optional[str] = None):
        """
        初始化工具
        
        Args:
            working_dir: 工作目录（可选，默认当前目录）
        """
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        
        # 安全白名单命令
        self.safe_commands = {
            # 文件浏览
            "ls", "dir", "tree", "find", "locate",
            # 文件内容
            "cat", "head", "tail", "less", "more",
            # 文件信息
            "stat", "file", "wc", "du",
            # 搜索
            "grep", "rg", "ag",
            # Git
            "git",
            # Python
            "python", "python3",
            # 系统信息
            "pwd", "whoami", "uname", "hostname"
        }
        
        # 命令历史
        self.command_history: List[Dict[str, Any]] = []
        
        # 统计信息
        self.stats = {
            "total_commands": 0,
            "successful": 0,
            "failed": 0
        }
    
    def execute(self, 
                command: str, 
                capture_output: bool = True,
                timeout: int = 30,
                check_safety: bool = True) -> Dict[str, Any]:
        """
        执行 shell 命令
        
        Args:
            command: 命令字符串
            capture_output: 是否捕获输出
            timeout: 超时时间（秒）
            check_safety: 是否检查命令安全性
            
        Returns:
            包含执行结果的字典
        """
        result = {
            "command": command,
            "success": False,
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "duration": 0
        }
        
        try:
            # 安全检查
            if check_safety and not self._is_safe_command(command):
                error_msg = f"⚠️ 不安全命令被拒绝：{command}"
                result["stderr"] = error_msg
                print(error_msg)
                return result
            
            # 记录命令
            self.command_history.append({
                "command": command,
                "timestamp": __import__('datetime').datetime.now().isoformat()
            })
            
            # 执行命令
            import time
            start_time = time.time()
            
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.working_dir),
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
            
            result["stdout"] = proc.stdout or ""
            result["stderr"] = proc.stderr or ""
            result["return_code"] = proc.returncode
            result["success"] = (proc.returncode == 0)
            result["duration"] = time.time() - start_time
            
            # 更新统计
            self.stats["total_commands"] += 1
            if result["success"]:
                self.stats["successful"] += 1
            else:
                self.stats["failed"] += 1
            
            # 打印输出（如果不太长）
            if capture_output:
                output_lines = result["stdout"].split('\n')
                if len(output_lines) <= 50:
                    print(result["stdout"])
                else:
                    print(f"[输出共 {len(output_lines)} 行，已截断显示前 50 行]")
                    print('\n'.join(output_lines[:50]))
                    print("...")
            
            return result
            
        except subprocess.TimeoutExpired:
            result["stderr"] = f"命令执行超时（>{timeout}秒）"
            print(f"❌ {result['stderr']}")
            return result
            
        except Exception as e:
            result["stderr"] = str(e)
            print(f"❌ 命令执行失败：{e}")
            return result
    
    def explore_directory(self, 
                         path: Optional[str] = None,
                         depth: int = 2,
                         show_hidden: bool = False) -> str:
        """
        探索目录结构
        
        Args:
            path: 目录路径（可选，默认工作目录）
            depth: 递归深度
            show_hidden: 是否显示隐藏文件
            
        Returns:
            目录结构字符串
        """
        target_path = path if path else str(self.working_dir)
        
        # 使用 tree 或 ls 命令
        try:
            if show_hidden:
                cmd = f"ls -la {'-R' * depth} {target_path}"
            else:
                cmd = f"ls -l {'-R' * depth} {target_path}"
            
            result = self.execute(cmd, check_safety=False)
            return result["stdout"] if result["success"] else result["stderr"]
            
        except Exception as e:
            return f"探索目录失败：{e}"
    
    def view_file(self, 
                 filepath: str,
                 lines: int = 50,
                 from_end: bool = True) -> str:
        """
        查看文件内容
        
        Args:
            filepath: 文件路径
            lines: 显示行数
            from_end: 从文件末尾开始
            
        Returns:
            文件内容字符串
        """
        try:
            if from_end:
                cmd = f"tail -n {lines} {filepath}"
            else:
                cmd = f"head -n {lines} {filepath}"
            
            result = self.execute(cmd, check_safety=False)
            return result["stdout"] if result["success"] else result["stderr"]
            
        except Exception as e:
            return f"查看文件失败：{e}"
    
    def search_code(self, 
                   pattern: str,
                   file_pattern: str = "*.py",
                   case_sensitive: bool = False) -> str:
        """
        搜索代码
        
        Args:
            pattern: 搜索模式
            file_pattern: 文件匹配模式
            case_sensitive: 是否区分大小写
            
        Returns:
            搜索结果字符串
        """
        try:
            # 优先使用 rg (ripgrep)，其次使用 grep
            flags = "-n"  # 显示行号
            if not case_sensitive:
                flags += "i"
            
            cmd = f"rg {flags} '{pattern}' --glob '{file_pattern}'"
            result = self.execute(cmd, check_safety=False)
            
            if result["success"]:
                return result["stdout"]
            else:
                # 回退到 grep
                cmd = f"grep -r {flags} '{pattern}' --include='{file_pattern}'"
                result = self.execute(cmd, check_safety=False)
                return result["stdout"] if result["success"] else result["stderr"]
                
        except Exception as e:
            return f"搜索代码失败：{e}"
    
    def get_file_stats(self, filepath: str) -> Dict[str, Any]:
        """
        获取文件统计信息
        
        Args:
            filepath: 文件路径
            
        Returns:
            包含文件信息的字典
        """
        try:
            path = Path(filepath)
            
            if not path.exists():
                return {"error": "文件不存在"}
            
            stats = path.stat()
            
            # 计算行数
            line_count = 0
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for _ in f)
            except:
                line_count = -1
            
            return {
                "path": str(path),
                "name": path.name,
                "size_bytes": stats.st_size,
                "size_kb": round(stats.st_size / 1024, 2),
                "lines": line_count,
                "created_at": __import__('datetime').datetime.fromtimestamp(stats.st_ctime).isoformat(),
                "modified_at": __import__('datetime').datetime.fromtimestamp(stats.st_mtime).isoformat(),
                "is_file": path.is_file(),
                "is_dir": path.is_dir()
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def git_status(self) -> str:
        """获取 Git 状态"""
        return self.explore_git("status")
    
    def explore_git(self, subcommand: str = "log", limit: int = 10) -> str:
        """
        探索 Git 历史
        
        Args:
            subcommand: Git 子命令 (log, diff, branch 等)
            limit: 限制数量
            
        Returns:
            Git 信息字符串
        """
        try:
            if subcommand == "log":
                cmd = f"git log --oneline -n {limit}"
            elif subcommand == "diff":
                cmd = "git diff --stat"
            elif subcommand == "branch":
                cmd = "git branch -a"
            else:
                cmd = f"git {subcommand}"
            
            result = self.execute(cmd, check_safety=False)
            return result["stdout"] if result["success"] else result["stderr"]
            
        except Exception as e:
            return f"Git 操作失败：{e}"
    
    def _is_safe_command(self, command: str) -> bool:
        """
        检查命令是否安全
        
        策略：
        - 只允许白名单中的命令
        - 禁止危险命令（rm -rf, sudo 等）
        """
        # 提取主命令（第一个单词）
        parts = command.split()
        if not parts:
            return False
        
        main_cmd = parts[0].lower()
        
        # 检查是否在白名单中
        if main_cmd not in self.safe_commands:
            return False
        
        # 检查危险模式
        dangerous_patterns = ["rm -rf", "sudo", "chmod 777", "> /dev/", ">> /etc/", "| sudo"]
        for pattern in dangerous_patterns:
            if pattern in command.lower():
                return False
        
        return True
    
    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取命令历史"""
        return self.command_history[-limit:]
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        return {
            **self.stats,
            "working_directory": str(self.working_dir),
            "recent_commands": [cmd["command"] for cmd in self.get_history(5)]
        }
