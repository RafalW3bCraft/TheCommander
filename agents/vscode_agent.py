import os
import json
import logging
import subprocess
import re
from pathlib import Path
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class VSCodeAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(
            name="VSCodeAgent",
            description="Specialized in Visual Studio Code and Linux integration."
        )
    
    def get_commands(self):
        return {
            "install-extension": {
                "description": "Install a VS Code extension",
                "usage": "install-extension <extension_id>",
                "examples": [
                    "install-extension ms-python.python",
                    "install-extension dbaeumer.vscode-eslint"
                ]
            },
            "create-task": {
                "description": "Create a VS Code task configuration",
                "usage": "create-task <task_name> <command> [args]",
                "examples": [
                    "create-task build 'npm run build'",
                    "create-task test 'python -m unittest discover'"
                ]
            },
            "create-launch": {
                "description": "Create a VS Code launch/debug configuration",
                "usage": "create-launch <name> <type> [program]",
                "examples": [
                    "create-launch 'Python Debug' python app.py",
                    "create-launch 'Node Server' node server.js"
                ]
            },
            "workspace-setting": {
                "description": "Create or update a workspace setting",
                "usage": "workspace-setting <setting_name> <value>",
                "examples": [
                    "workspace-setting editor.tabSize 2",
                    "workspace-setting python.linting.enabled true"
                ]
            },
            "create-keybinding": {
                "description": "Create a custom keybinding for VS Code",
                "usage": "create-keybinding <key> <command>",
                "examples": [
                    "create-keybinding 'ctrl+alt+t' 'workbench.action.terminal.new'",
                    "create-keybinding 'ctrl+shift+r' 'editor.action.startFindReplaceAction'"
                ]
            },
            "linux-terminal": {
                "description": "Create a VS Code terminal profile for Linux",
                "usage": "linux-terminal <name> <shell_path>",
                "examples": [
                    "linux-terminal bash /bin/bash",
                    "linux-terminal zsh /usr/bin/zsh"
                ]
            },
            "recommend-extensions": {
                "description": "Get recommended VS Code extensions based on project type",
                "usage": "recommend-extensions <project_type>",
                "examples": [
                    "recommend-extensions python",
                    "recommend-extensions javascript",
                    "recommend-extensions web"
                ]
            },
            "list-extensions": {
                "description": "List installed VS Code extensions",
                "usage": "list-extensions",
                "examples": ["list-extensions"]
            }
        }
    
    def execute(self, command, args):
        try:
            if command == "install-extension":
                if not args:
                    return "Error: Missing extension ID. Usage: install-extension <extension_id>"
                extension_id = args[0]
                return self._install_extension(extension_id)
                
            elif command == "create-task":
                if len(args) < 2:
                    return "Error: Missing task name or command. Usage: create-task <task_name> <command> [args]"
                task_name = args[0]
                task_command = " ".join(args[1:])
                return self._create_task(task_name, task_command)
                
            elif command == "create-launch":
                if len(args) < 2:
                    return "Error: Missing configuration details. Usage: create-launch <name> <type> [program]"
                config_name = args[0]
                config_type = args[1]
                program = args[2] if len(args) > 2 else None
                return self._create_launch_config(config_name, config_type, program)
                
            elif command == "workspace-setting":
                if len(args) < 2:
                    return "Error: Missing setting name or value. Usage: workspace-setting <setting_name> <value>"
                setting_name = args[0]
                setting_value = " ".join(args[1:])
                return self._update_workspace_setting(setting_name, setting_value)
                
            elif command == "create-keybinding":
                if len(args) < 2:
                    return "Error: Missing key or command. Usage: create-keybinding <key> <command>"
                key = args[0]
                command_name = " ".join(args[1:])
                return self._create_keybinding(key, command_name)
                
            elif command == "linux-terminal":
                if len(args) < 2:
                    return "Error: Missing terminal name or shell path. Usage: linux-terminal <name> <shell_path>"
                terminal_name = args[0]
                shell_path = args[1]
                return self._create_linux_terminal(terminal_name, shell_path)
                
            elif command == "recommend-extensions":
                if not args:
                    return "Error: Missing project type. Usage: recommend-extensions <project_type>"
                project_type = args[0].lower()
                return self._recommend_extensions(project_type)
                
            elif command == "list-extensions":
                return self._list_extensions()
                
            else:
                return f"Unknown command: '{command}'"
                
        except Exception as e:
            logger.error(f"Error in VSCodeAgent: {str(e)}")
            return f"Error executing command: {str(e)}"
    
    def _vscode_dir_exists(self):
        vscode_dir = Path(".vscode")
        if not vscode_dir.exists():
            vscode_dir.mkdir()
            logger.debug("Created .vscode directory")
        return vscode_dir
    
    def _install_extension(self, extension_id):
        try:
            logger.debug(f"Installing VS Code extension: {extension_id}")
            
            return f"""
To install the VS Code extension '{extension_id}':

1. Command for local VS Code:
   code --install-extension {extension_id}

2. Alternative manual installation method:
   - Open VS Code
   - Go to Extensions view (Ctrl+Shift+X)
   - Search for '{extension_id}'
   - Click Install

Note: This agent is running in a web environment and cannot directly install 
VS Code extensions on your local machine.
"""
            
        except Exception as e:
            logger.error(f"Error installing extension: {str(e)}")
            return f"Error installing extension: {str(e)}"
    
    def _create_task(self, task_name, task_command):
        try:
            logger.debug(f"Creating VS Code task: {task_name} -> {task_command}")
            
            vscode_dir = self._vscode_dir_exists()
            tasks_file = vscode_dir / "tasks.json"
            
            new_task = {
                "label": task_name,
                "type": "shell",
                "command": task_command,
                "problemMatcher": [],
                "group": {
                    "kind": "build",
                    "isDefault": False
                }
            }
            
            if tasks_file.exists():
                with open(tasks_file, 'r') as f:
                    try:
                        tasks_config = json.load(f)
                    except json.JSONDecodeError:
                        tasks_config = {"version": "2.0.0", "tasks": []}
            else:
                tasks_config = {"version": "2.0.0", "tasks": []}
            
            if "tasks" not in tasks_config:
                tasks_config["tasks"] = []
            
            task_exists = False
            for i, task in enumerate(tasks_config["tasks"]):
                if task.get("label") == task_name:
                    tasks_config["tasks"][i] = new_task
                    task_exists = True
                    break
            
            if not task_exists:
                tasks_config["tasks"].append(new_task)
            
            with open(tasks_file, 'w') as f:
                json.dump(tasks_config, f, indent=4)
            
            return f"VS Code task '{task_name}' created successfully.\n\nTo run this task:\n1. Open VS Code\n2. Press Ctrl+Shift+P\n3. Type 'Tasks: Run Task' and select '{task_name}'"
            
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            return f"Error creating task: {str(e)}"
    
    def _create_launch_config(self, config_name, config_type, program=None):
        try:
            logger.debug(f"Creating VS Code launch config: {config_name} ({config_type})")
            
            vscode_dir = self._vscode_dir_exists()
            launch_file = vscode_dir / "launch.json"
            
            launch_config = {
                "name": config_name,
                "type": config_type,
                "request": "launch",
            }
            
            if config_type.lower() == "python":
                launch_config.update({
                    "program": program or "${file}",
                    "console": "integratedTerminal",
                    "justMyCode": True
                })
            elif config_type.lower() == "node":
                launch_config.update({
                    "program": program or "${file}",
                    "skipFiles": ["<node_internals>/**"],
                    "console": "integratedTerminal"
                })
            elif config_type.lower() == "chrome":
                launch_config.update({
                    "url": "http://localhost:3000",
                    "webRoot": "${workspaceFolder}"
                })
            
            if launch_file.exists():
                with open(launch_file, 'r') as f:
                    try:
                        launch_obj = json.load(f)
                    except json.JSONDecodeError:
                        launch_obj = {"version": "0.2.0", "configurations": []}
            else:
                launch_obj = {"version": "0.2.0", "configurations": []}
            
            if "configurations" not in launch_obj:
                launch_obj["configurations"] = []
            
            config_exists = False
            for i, config in enumerate(launch_obj["configurations"]):
                if config.get("name") == config_name:
                    launch_obj["configurations"][i] = launch_config
                    config_exists = True
                    break
            
            if not config_exists:
                launch_obj["configurations"].append(launch_config)
            
            with open(launch_file, 'w') as f:
                json.dump(launch_obj, f, indent=4)
            
            return f"VS Code debug configuration '{config_name}' created successfully.\n\nTo use this configuration:\n1. Open VS Code\n2. Press F5 or go to Run > Start Debugging\n3. Select '{config_name}' from the dropdown menu"
            
        except Exception as e:
            logger.error(f"Error creating launch configuration: {str(e)}")
            return f"Error creating launch configuration: {str(e)}"
    
    def _update_workspace_setting(self, setting_name, setting_value):
        try:
            logger.debug(f"Updating workspace setting: {setting_name} = {setting_value}")
            
            vscode_dir = self._vscode_dir_exists()
            settings_file = vscode_dir / "settings.json"
            
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    try:
                        settings = json.load(f)
                    except json.JSONDecodeError:
                        settings = {}
            else:
                settings = {}
            
            try:
                if setting_value.lower() == "true":
                    parsed_value = True
                elif setting_value.lower() == "false":
                    parsed_value = False
                elif setting_value.isdigit():
                    parsed_value = int(setting_value)
                elif re.match(r'^-?\d+\.\d+$', setting_value):
                    parsed_value = float(setting_value)
                elif setting_value.startswith('[') and setting_value.endswith(']'):
                    parsed_value = json.loads(setting_value)
                elif setting_value.startswith('{') and setting_value.endswith('}'):
                    parsed_value = json.loads(setting_value)
                else:
                    parsed_value = setting_value
            except:
                parsed_value = setting_value
            
            settings[setting_name] = parsed_value
            
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            
            return f"VS Code workspace setting '{setting_name}' updated to '{setting_value}' successfully."
            
        except Exception as e:
            logger.error(f"Error updating workspace setting: {str(e)}")
            return f"Error updating workspace setting: {str(e)}"
    
    def _create_keybinding(self, key, command_name):
        try:
            logger.debug(f"Creating keybinding: {key} -> {command_name}")
            
            return f"""
To create the VS Code keybinding '{key}' for command '{command_name}':

1. Open VS Code
2. Press Ctrl+Shift+P
3. Type "Preferences: Open Keyboard Shortcuts (JSON)"
4. Add the following entry to the JSON file:

{{
    "key": "{key}",
    "command": "{command_name}",
    "when": "editorTextFocus"
}}

Note: You may need to adjust the "when" clause depending on when you want 
the keybinding to be active.
"""
            
        except Exception as e:
            logger.error(f"Error creating keybinding: {str(e)}")
            return f"Error creating keybinding: {str(e)}"
    
    def _create_linux_terminal(self, terminal_name, shell_path):
        try:
            logger.debug(f"Creating Linux terminal profile: {terminal_name} -> {shell_path}")
            
            vscode_dir = self._vscode_dir_exists()
            settings_file = vscode_dir / "settings.json"
            
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    try:
                        settings = json.load(f)
                    except json.JSONDecodeError:
                        settings = {}
            else:
                settings = {}
            
            if not os.path.exists(shell_path):
                return f"Warning: The shell path '{shell_path}' does not exist. Creating terminal profile anyway."
            
            if "terminal.integrated.profiles.linux" not in settings:
                settings["terminal.integrated.profiles.linux"] = {}
            
            settings["terminal.integrated.profiles.linux"][terminal_name] = {
                "path": shell_path,
                "icon": "terminal-linux"
            }
            
            if len(settings["terminal.integrated.profiles.linux"]) == 1:
                settings["terminal.integrated.defaultProfile.linux"] = terminal_name
            
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            
            return f"VS Code Linux terminal profile '{terminal_name}' created successfully with shell path '{shell_path}'.\n\nTo use this terminal:\n1. Open VS Code\n2. Press Ctrl+` to open a terminal\n3. Click the dropdown in the terminal panel and select '{terminal_name}'"
            
        except Exception as e:
            logger.error(f"Error creating Linux terminal profile: {str(e)}")
            return f"Error creating Linux terminal profile: {str(e)}"
    
    def _recommend_extensions(self, project_type):
        try:
            logger.debug(f"Getting recommended extensions for project type: {project_type}")
            
            recommendations = {
                "python": [
                    {"id": "ms-python.python", "name": "Python", "description": "IntelliSense, linting, debugging, etc."},
                    {"id": "ms-python.vscode-pylance", "name": "Pylance", "description": "Fast, feature-rich language support"},
                    {"id": "ms-toolsai.jupyter", "name": "Jupyter", "description": "Jupyter notebook support"},
                    {"id": "njpwerner.autodocstring", "name": "autoDocstring", "description": "Generate Python docstrings"}
                ],
                "javascript": [
                    {"id": "dbaeumer.vscode-eslint", "name": "ESLint", "description": "Integrates ESLint into VS Code"},
                    {"id": "esbenp.prettier-vscode", "name": "Prettier", "description": "Code formatter"},
                    {"id": "ms-vscode.vscode-typescript-next", "name": "TypeScript Next", "description": "TypeScript support"},
                    {"id": "christian-kohler.npm-intellisense", "name": "npm Intellisense", "description": "Autocompletes npm modules"}
                ],
                "web": [
                    {"id": "ritwickdey.LiveServer", "name": "Live Server", "description": "Local dev server with live reload"},
                    {"id": "formulahendry.auto-close-tag", "name": "Auto Close Tag", "description": "Automatically close HTML/XML tags"},
                    {"id": "bradlc.vscode-tailwindcss", "name": "Tailwind CSS IntelliSense", "description": "Intelligent Tailwind CSS tooling"},
                    {"id": "ecmel.vscode-html-css", "name": "HTML CSS Support", "description": "CSS support for HTML documents"}
                ],
                "docker": [
                    {"id": "ms-azuretools.vscode-docker", "name": "Docker", "description": "Docker container support"},
                    {"id": "ms-vscode-remote.remote-containers", "name": "Remote - Containers", "description": "Open any folder inside a container"}
                ],
                "linux": [
                    {"id": "ms-vscode-remote.remote-ssh", "name": "Remote - SSH", "description": "Connect to remote Linux via SSH"},
                    {"id": "timonwong.shellcheck", "name": "ShellCheck", "description": "Lint shell scripts"},
                    {"id": "rogalmic.bash-debug", "name": "Bash Debug", "description": "Bash script debugging"}
                ],
                "git": [
                    {"id": "eamodio.gitlens", "name": "GitLens", "description": "Powerful Git capabilities"},
                    {"id": "mhutchie.git-graph", "name": "Git Graph", "description": "View Git graph"},
                    {"id": "donjayamanne.githistory", "name": "Git History", "description": "View git log, file history"}
                ]
            }
            
            if project_type not in recommendations:
                return f"Project type '{project_type}' not recognized. Available types: {', '.join(recommendations.keys())}"
            
            vscode_dir = self._vscode_dir_exists()
            extensions_file = vscode_dir / "extensions.json"
            
            project_extensions = recommendations[project_type]
            
            extensions_json = {
                "recommendations": [ext["id"] for ext in project_extensions]
            }
            
            with open(extensions_file, 'w') as f:
                json.dump(extensions_json, f, indent=4)
            
            result = f"Recommended VS Code Extensions for {project_type.title()} Projects:\n\n"
            for ext in project_extensions:
                result += f"1. {ext['name']} ({ext['id']})\n   {ext['description']}\n\n"
            
            result += f"These have been added to .vscode/extensions.json. When users open this project in VS Code, they will be prompted to install these recommended extensions."
            
            return result
            
        except Exception as e:
            logger.error(f"Error recommending extensions: {str(e)}")
            return f"Error recommending extensions: {str(e)}"
    
    def _list_extensions(self):
        return """
To list VS Code extensions on your system, run one of these commands in your terminal:

1. List all installed extensions:
   code --list-extensions

2. List with details:
   code --list-extensions --show-versions

3. Inside VS Code:
   - Use the Extensions view (Ctrl+Shift+X)
   - Click on the "..." menu in the Extensions view
   - Select "Show Installed Extensions"

Note: This agent is running in a web environment and cannot directly access
your local VS Code installation.
"""
