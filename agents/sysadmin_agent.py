import os
import subprocess
import platform
import logging
import shutil
import psutil
from pathlib import Path
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class SysAdminAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(
            name="SysAdminAgent",
            description="Specialized in server management and deployment."
        )
        self.dangerous_commands = [
            "rm -rf", "sudo", "chmod", "chown", "> /dev/", "format", "mkfs", "dd",
            "> /proc", "mv /*", "echo > /dev/", ":(){ :|:& };:", "> /etc/passwd"
        ]
    
    def get_commands(self):
        return {
            "exec": {
                "description": "Execute a shell command safely",
                "usage": "exec <command>",
                "examples": [
                    "exec ls -la",
                    "exec pwd",
                    "exec ps aux | grep python"
                ]
            },
            "sysinfo": {
                "description": "Get information about the system",
                "usage": "sysinfo",
                "examples": ["sysinfo"]
            },
            "diskspace": {
                "description": "Get disk usage information",
                "usage": "diskspace [path]",
                "examples": [
                    "diskspace",
                    "diskspace /home"
                ]
            },
            "processes": {
                "description": "List running processes",
                "usage": "processes [filter]",
                "examples": [
                    "processes",
                    "processes python"
                ]
            },
            "meminfo": {
                "description": "Get memory usage information",
                "usage": "meminfo",
                "examples": ["meminfo"]
            },
            "find": {
                "description": "Find files in a directory",
                "usage": "find <path> <pattern>",
                "examples": [
                    "find . *.py",
                    "find /var/log *.log"
                ]
            }
        }
    
    def execute(self, command, args):
        try:
            if command == "exec":
                if not args:
                    return "Error: Missing command to execute. Usage: exec <command>"
                shell_command = " ".join(args)
                return self._execute_shell(shell_command)
                
            elif command == "sysinfo":
                return self._get_system_info()
                
            elif command == "diskspace":
                path = args[0] if args else "."
                return self._get_disk_space(path)
                
            elif command == "processes":
                filter_term = args[0] if args else None
                return self._list_processes(filter_term)
                
            elif command == "meminfo":
                return self._get_memory_info()
                
            elif command == "find":
                if len(args) < 2:
                    return "Error: Missing path or pattern. Usage: find <path> <pattern>"
                path = args[0]
                pattern = args[1]
                return self._find_files(path, pattern)
                
            else:
                return f"Unknown command: '{command}'"
                
        except Exception as e:
            logger.error(f"Error in SysAdminAgent: {str(e)}")
            return f"Error executing command: {str(e)}"
    
    def _is_safe_command(self, command):
        for dangerous in self.dangerous_commands:
            if dangerous in command:
                return False
        return True
    
    def _execute_shell(self, command):
        try:
            logger.debug(f"Executing shell command: {command}")
            
            if not self._is_safe_command(command):
                return f"Error: The command '{command}' contains potentially harmful operations and is not allowed."
            
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=15
            )
            
            output = result.stdout
            error = result.stderr
            
            if result.returncode != 0:
                return f"Command executed with errors (return code {result.returncode}):\n{error}"
            
            if not output and not error:
                return "Command executed successfully (no output)."
            
            return output if output else error
        
        except subprocess.TimeoutExpired:
            return "Error: Command execution timed out (15 seconds limit)."
        except Exception as e:
            logger.error(f"Error executing shell command: {str(e)}")
            return f"Error executing command: {str(e)}"
    
    def _get_system_info(self):
        try:
            result = "System Information:\n\n"
            
            result += f"OS: {platform.system()} {platform.release()}\n"
            result += f"Platform: {platform.platform()}\n"
            result += f"Python Version: {platform.python_version()}\n"
            
            cpu_count = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            result += f"CPU Cores: {cpu_count} physical, {cpu_count_logical} logical\n"
            result += f"CPU Usage: {psutil.cpu_percent(interval=1)}%\n"
            
            mem = psutil.virtual_memory()
            result += f"Memory: {self._format_bytes(mem.total)} total, {self._format_bytes(mem.available)} available\n"
            result += f"Memory Usage: {mem.percent}%\n"
            
            disk = psutil.disk_usage('/')
            result += f"Disk: {self._format_bytes(disk.total)} total, {self._format_bytes(disk.free)} free\n"
            result += f"Disk Usage: {disk.percent}%\n"
            
            addresses = []
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == 2:
                        addresses.append(f"{interface}: {addr.address}")
            
            if addresses:
                result += "\nNetwork Interfaces:\n"
                for addr in addresses:
                    result += f"- {addr}\n"
            
            result += "\nEnvironment Variables:\n"
            safe_vars = ["PATH", "PYTHONPATH", "HOME", "USER", "SHELL", "LANG", "PWD"]
            for var in safe_vars:
                if var in os.environ:
                    result += f"- {var}: {os.environ.get(var)}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return f"Error getting system info: {str(e)}"
    
    def _format_bytes(self, bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} PB"
    
    def _get_disk_space(self, path):
        try:
            logger.debug(f"Getting disk space for path: {path}")
            
            if not os.path.exists(path):
                return f"Error: Path '{path}' does not exist."
            
            disk_usage = shutil.disk_usage(path)
            
            result = f"Disk Usage for {path}:\n\n"
            result += f"Total Space: {self._format_bytes(disk_usage.total)}\n"
            result += f"Used Space: {self._format_bytes(disk_usage.used)} ({disk_usage.used / disk_usage.total:.1%})\n"
            result += f"Free Space: {self._format_bytes(disk_usage.free)} ({disk_usage.free / disk_usage.total:.1%})\n"
            
            if os.path.isdir(path):
                try:
                    dir_size = self._get_dir_size(path)
                    result += f"\nDirectory Size: {self._format_bytes(dir_size)}\n"
                    
                    result += "\nLargest Subdirectories:\n"
                    subdirs = []
                    
                    for item in os.listdir(path):
                        item_path = os.path.join(path, item)
                        if os.path.isdir(item_path):
                            try:
                                size = self._get_dir_size(item_path)
                                subdirs.append((item, size))
                            except:
                                continue
                    
                    subdirs.sort(key=lambda x: x[1], reverse=True)
                    for i, (subdir, size) in enumerate(subdirs[:5], 1):
                        result += f"{i}. {subdir}: {self._format_bytes(size)}\n"
                    
                except Exception as dir_e:
                    result += f"\nCould not calculate directory size: {str(dir_e)}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting disk space: {str(e)}")
            return f"Error getting disk space: {str(e)}"
    
    def _get_dir_size(self, path):
        total_size = 0
        for dirpath, _, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path) and not os.path.islink(file_path):
                    total_size += os.path.getsize(file_path)
        return total_size
    
    def _list_processes(self, filter_term=None):
        try:
            logger.debug(f"Listing processes with filter: {filter_term}")
            
            result = "Running Processes:\n\n"
            result += f"{'PID':<7} {'CPU%':<6} {'Memory%':<8} {'Name':<30} Command\n"
            result += "-" * 80 + "\n"
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    if filter_term:
                        if filter_term.lower() not in proc.info['name'].lower() and not any(
                            filter_term.lower() in cmd.lower() for cmd in proc.info['cmdline'] if cmd
                        ):
                            continue
                    
                    cmd = " ".join(proc.info['cmdline']) if proc.info['cmdline'] else "[No command]"
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmd': cmd,
                        'cpu': proc.info['cpu_percent'],
                        'memory': proc.info['memory_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            processes.sort(key=lambda x: x['memory'], reverse=True)
            
            for proc in processes[:20]:
                result += f"{proc['pid']:<7} {proc['cpu']:<6.1f} {proc['memory']:<8.1f} {proc['name'][:30]:<30} {proc['cmd'][:50]}\n"
            
            if len(processes) > 20:
                result += f"\n... and {len(processes) - 20} more processes."
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing processes: {str(e)}")
            return f"Error listing processes: {str(e)}"
    
    def _get_memory_info(self):
        try:
            logger.debug("Getting memory information")
            
            vm = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            result = "Memory Information:\n\n"
            result += "Virtual Memory:\n"
            result += f"Total: {self._format_bytes(vm.total)}\n"
            result += f"Available: {self._format_bytes(vm.available)} ({vm.available / vm.total:.1%})\n"
            result += f"Used: {self._format_bytes(vm.used)} ({vm.percent}%)\n"
            result += f"Free: {self._format_bytes(vm.free)}\n"
            
            result += "\nSwap Memory:\n"
            result += f"Total: {self._format_bytes(swap.total)}\n"
            result += f"Used: {self._format_bytes(swap.used)} ({swap.percent}%)\n"
            result += f"Free: {self._format_bytes(swap.free)}\n"
            
            result += "\nTop Memory-Consuming Processes:\n"
            result += f"{'PID':<7} {'Memory%':<8} {'Name':<30} Command\n"
            result += "-" * 80 + "\n"
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent']):
                try:
                    cmd = " ".join(proc.info['cmdline']) if proc.info['cmdline'] else "[No command]"
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmd': cmd,
                        'memory': proc.info['memory_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            processes.sort(key=lambda x: x['memory'], reverse=True)
            for proc in processes[:10]:
                result += f"{proc['pid']:<7} {proc['memory']:<8.1f} {proc['name'][:30]:<30} {proc['cmd'][:50]}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting memory info: {str(e)}")
            return f"Error getting memory info: {str(e)}"
    
    def _find_files(self, path, pattern):
        try:
            logger.debug(f"Finding files in {path} matching pattern: {pattern}")
            
            if not os.path.exists(path):
                return f"Error: Path '{path}' does not exist."
            
            if not os.path.isdir(path):
                return f"Error: '{path}' is not a directory."
            
            p = Path(path)
            matches = list(p.glob(pattern))
            
            if not matches:
                return f"No files found in '{path}' matching pattern '{pattern}'."
            
            result = f"Files matching '{pattern}' in '{path}':\n\n"
            
            files = []
            dirs = []
            
            for match in matches:
                if match.is_dir():
                    dirs.append(match)
                else:
                    try:
                        size = os.path.getsize(match)
                        files.append((match, size))
                    except:
                        files.append((match, 0))
            
            if dirs:
                result += "Directories:\n"
                for i, dir_path in enumerate(sorted(dirs), 1):
                    result += f"{i}. {dir_path.name}/\n"
                result += "\n"
            
            if files:
                files.sort(key=lambda x: x[0].name)
                result += "Files:\n"
                for i, (file_path, size) in enumerate(files, 1):
                    result += f"{i}. {file_path.name} ({self._format_bytes(size)})\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error finding files: {str(e)}")
            return f"Error finding files: {str(e)}"
