import re
import shlex
import logging
import json
from typing import Tuple, List, Dict, Any, Optional, Union

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def parse_command(command_text: str) -> Tuple[str, List[str]]:
    try:
        args = shlex.split(command_text)
        
        if not args:
            return ("help", [])
        
        command = args[0].lower()
        arguments = args[1:]
        
        logger.debug(f"Parsed command: {command}, args: {arguments}")
        return (command, arguments)
    except Exception as e:
        logger.error(f"Error parsing command: {str(e)}")
        return ("error", [f"Could not parse command: {str(e)}"])

def advanced_parse_command(command_text: str) -> Dict[str, Any]:
    try:
        tokens = shlex.split(command_text)
        
        if not tokens:
            return {
                "command": "help",
                "subcommand": None,
                "args": [],
                "options": {},
                "original_text": command_text
            }
        
        result = {
            "command": tokens[0].lower(),
            "subcommand": None,
            "args": [],
            "options": {},
            "original_text": command_text
        }
        
        agent_commands = [
            "coder", "researcher", "sysadmin", "memory", "vscode", 
            "security", "database", "devops", "learning"
        ]
        
        remaining_tokens = tokens[1:]
        
        if result["command"] in agent_commands and remaining_tokens:
            result["subcommand"] = remaining_tokens[0].lower()
            remaining_tokens = remaining_tokens[1:]
        
        if result["command"] == "file" and remaining_tokens:
            result["subcommand"] = remaining_tokens[0].lower()
            remaining_tokens = remaining_tokens[1:]
        
        i = 0
        while i < len(remaining_tokens):
            token = remaining_tokens[i]
            
            if token.startswith("--"):
                option_parts = token[2:].split("=", 1)
                if len(option_parts) == 2:
                    key, value = option_parts
                    try:
                        if value.lower() == "true":
                            value = True
                        elif value.lower() == "false":
                            value = False
                        elif value.isdigit():
                            value = int(value)
                        elif re.match(r"^\d+\.\d+$", value):
                            value = float(value)
                    except:
                        pass
                    result["options"][key] = value
                else:
                    result["options"][option_parts[0]] = True
            elif ":" in token and not token.startswith(("http:", "https:")):
                key, value = token.split(":", 1)
                result["options"][key] = value
            elif "=" in token and not token.startswith(("http:", "https:")):
                key, value = token.split("=", 1)
                result["options"][key] = value
            else:
                result["args"].append(token)
            
            i += 1
        
        logger.debug(f"Advanced parsed command: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in advanced parsing: {str(e)}")
        return {
            "command": "error",
            "subcommand": None,
            "args": [f"Could not parse command: {str(e)}"],
            "options": {},
            "original_text": command_text
        }

def parse_natural_language_command(command_text: str, ai_service=None, available_commands=None) -> Dict[str, Any]:
    if re.match(r"^[a-zA-Z]+((\s+[a-zA-Z0-9_\-\.]+)+|\s*$)", command_text):
        return advanced_parse_command(command_text)
        
    if ai_service and hasattr(ai_service, 'understand_command'):
        try:
            context = {"available_commands": available_commands} if available_commands else None
            result = ai_service.understand_command(command_text, context=context)
            
            if isinstance(result, dict) and "command" in result and not "error" in result:
                result["original_text"] = command_text
                return result
        except Exception as e:
            logger.warning(f"Error using AI service for command parsing: {str(e)}")
    
    return advanced_parse_command(command_text)

def format_response(response):
    if isinstance(response, dict) or isinstance(response, list):
        try:
            return json.dumps(response, indent=2)
        except:
            return str(response)
    
    return str(response)

def sanitize_input(input_text):
    sanitized = re.sub(r'[;&|><$\n\r]', '', input_text)
    return sanitized

def find_similar_commands(command: str, available_commands: Dict[str, Any]) -> List[str]:
    if not command or not available_commands:
        return []
    
    prefix_matches = [cmd for cmd in available_commands.keys() 
                     if cmd.startswith(command[:1]) and cmd != command]
    
    lev_matches = []
    for cmd in available_commands.keys():
        if cmd != command and levenshtein_distance(command, cmd) <= 3:
            lev_matches.append(cmd)
    
    all_matches = list(set(prefix_matches + lev_matches))
    
    all_matches.sort(key=lambda x: levenshtein_distance(command, x))
    
    return all_matches[:5]

def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]
