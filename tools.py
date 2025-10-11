import os
import subprocess
import logging
import requests
import json
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class FileSystemTool:
    
    def read_file(self, filename):
        try:
            logger.debug(f"Reading file: {filename}")
            path = Path(filename)
            
            if not path.exists():
                return f"Error: File '{filename}' not found."
            
            if not path.is_file():
                return f"Error: '{filename}' is not a file."
            
            with open(filename, 'r') as file:
                content = file.read()
            
            return content
        except Exception as e:
            logger.error(f"Error reading file {filename}: {str(e)}")
            return f"Error reading file: {str(e)}"
    
    def write_file(self, filename, content):
        try:
            logger.debug(f"Writing to file: {filename}")
            with open(filename, 'w') as file:
                file.write(content)
            
            return f"Successfully wrote to '{filename}'."
        except Exception as e:
            logger.error(f"Error writing to file {filename}: {str(e)}")
            return f"Error writing to file: {str(e)}"
    
    def list_files(self, directory="."):
        try:
            logger.debug(f"Listing files in directory: {directory}")
            path = Path(directory)
            
            if not path.exists():
                return f"Error: Directory '{directory}' not found."
            
            if not path.is_dir():
                return f"Error: '{directory}' is not a directory."
            
            files = list(path.iterdir())
            
            result = f"Files in '{directory}':\n"
            for file in files:
                result += f"- {'📁 ' if file.is_dir() else '📄 '}{file.name}\n"
            
            return result
        except Exception as e:
            logger.error(f"Error listing files in {directory}: {str(e)}")
            return f"Error listing files: {str(e)}"
    
    def delete_file(self, filename):
        try:
            logger.debug(f"Deleting file: {filename}")
            path = Path(filename)
            
            if not path.exists():
                return f"Error: File '{filename}' not found."
            
            if path.is_dir():
                return f"Error: '{filename}' is a directory. Use a different command to delete directories."
            
            os.remove(filename)
            
            return f"Successfully deleted '{filename}'."
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {str(e)}")
            return f"Error deleting file: {str(e)}"
    
    def create_file(self, filename, content=""):
        try:
            logger.debug(f"Creating file: {filename}")
            path = Path(filename)
            
            if path.exists():
                return f"Error: File '{filename}' already exists."
            
            with open(filename, 'w') as file:
                file.write(content)
            
            return f"Successfully created '{filename}'."
        except Exception as e:
            logger.error(f"Error creating file {filename}: {str(e)}")
            return f"Error creating file: {str(e)}"


class TerminalTool:
    
    def __init__(self):
        self.forbidden_commands = [
            "rm -rf", "sudo", "chmod", "chown", 
            "> /dev/", "format", "mkfs", "dd"
        ]
    
    def is_safe_command(self, command):
        for forbidden in self.forbidden_commands:
            if forbidden in command:
                return False
        return True
    
    def execute(self, command):
        try:
            logger.debug(f"Executing terminal command: {command}")
            
            if not self.is_safe_command(command):
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
            logger.error(f"Error executing terminal command {command}: {str(e)}")
            return f"Error executing command: {str(e)}"


class ApiTool:
    
    def make_request(self, method, url, data=None, headers=None, **kwargs):
        try:
            logger.debug(f"Making API {method} request to: {url}")
            
            timeout = kwargs.get('timeout', 10)
            verify = kwargs.get('verify', True)
            auth = kwargs.get('auth', None)
            params = kwargs.get('params', None)
            cookies = kwargs.get('cookies', None)
            
            if data and isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    pass
            
            if headers and isinstance(headers, str):
                try:
                    headers = json.loads(headers)
                except json.JSONDecodeError:
                    headers = {"Content-Type": "application/json"}
            
            debug_info = {
                "method": method,
                "url": url,
                "has_data": data is not None,
                "has_headers": headers is not None,
                "timeout": timeout,
                "verify_ssl": verify,
                "has_auth": auth is not None
            }
            logger.debug(f"API request details: {debug_info}")
            
            response = requests.request(
                method=method,
                url=url,
                json=data if data and isinstance(data, dict) else None,
                data=data if data and not isinstance(data, dict) else None,
                headers=headers,
                timeout=timeout,
                verify=verify,
                auth=auth,
                params=params,
                cookies=cookies,
                **{k: v for k, v in kwargs.items() if k not in ['timeout', 'verify', 'auth', 'params', 'cookies']}
            )
            
            response_info = {
                "status_code": response.status_code,
                "reason": response.reason,
                "content_type": response.headers.get('Content-Type', ''),
                "elapsed_time": f"{response.elapsed.total_seconds():.2f}s"
            }
            
            output = {}
            output["request"] = {
                "method": method,
                "url": url,
                "headers": headers,
                "data_size": len(str(data)) if data else 0
            }
            output["response"] = response_info
            
            try:
                output["data"] = response.json()
            except json.JSONDecodeError:
                content = response.text
                preview = (content[:500] + '...') if len(content) > 500 else content
                output["text_preview"] = preview
                
                if response.headers.get('Content-Type', '').startswith('text/html'):
                    output["html"] = True
                
            return json.dumps(output, indent=2)
            
        except requests.RequestException as e:
            logger.error(f"Error making API request to {url}: {str(e)}")
            return json.dumps({
                "error": True,
                "type": "request_error",
                "message": str(e),
                "request": {
                    "method": method,
                    "url": url
                }
            }, indent=2)
        except Exception as e:
            logger.error(f"Error in API tool: {str(e)}")
            return json.dumps({
                "error": True,
                "type": "general_error",
                "message": str(e)
            }, indent=2)
