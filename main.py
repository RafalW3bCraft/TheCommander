import os
import base64
import logging
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, jsonify, send_file
from io import BytesIO
import requests
from command_center import command_center
from ai_service import ai_service
from task_service import task_service

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/')
def index():
    task_id = request.args.get('task')
    selected_task = task_service.get_task_template(task_id) if task_id else None
    
    return render_template('index.html', 
                          title="The Commander - AI Agent",
                          selected_task=selected_task)

@app.route('/tasks')
def tasks_page():
    return render_template('tasks.html', title="Task Workflows - The Commander")

@app.route('/help')
def help_page():
    commands = command_center.commander.get_available_commands()
    return render_template('help.html', title="Commander Help", commands=commands)

@app.route('/execute', methods=['POST'])
def execute_command():
    try:
        command = request.json.get('command', '')
        if not command:
            return jsonify({"status": "error", "message": "No command provided"}), 400
        
        use_advanced_parsing = request.json.get('use_advanced_parsing', True)
        use_ai = request.json.get('use_ai', True)
        
        result = command_center.execute_command(
            command, 
            use_advanced_parsing=use_advanced_parsing,
            use_ai=use_ai
        )
        
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/workflow', methods=['POST'])
def execute_workflow():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        source_agent = data.get('source', 'commander')
        target_agent = data.get('target')
        action = data.get('action')
        workflow_data = data.get('data', {})
        
        if not target_agent or not action:
            return jsonify({"status": "error", "message": "Missing target agent or action"}), 400
        
        result = command_center.agent_to_agent(source_agent, target_agent, action, workflow_data)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/history')
def get_history():
    try:
        limit = request.args.get('limit', default=10, type=int)
        history = command_center.get_task_history(limit)
        return jsonify({"status": "success", "history": history})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
@app.route('/command-suggestions')
def get_command_suggestions():
    try:
        query = request.args.get('query', '').lower()
        use_ai = request.args.get('use_ai', 'true').lower() == 'true'
        
        all_commands = command_center.commander.get_available_commands()
        
        suggestions = []
        
        if query and use_ai and len(query) > 3:
            try:
                from ai_service import ai_service
                from utils import parse_natural_language_command, find_similar_commands
                
                parsed_command = parse_natural_language_command(
                    query, 
                    ai_service=ai_service,
                    available_commands=all_commands
                )
                
                if parsed_command and "command" in parsed_command and parsed_command["command"] != "error":
                    cmd = parsed_command["command"]
                    subcommand = parsed_command.get("subcommand")
                    
                    command_text = cmd
                    if subcommand:
                        command_text += f" {subcommand}"
                        
                    if parsed_command.get("args"):
                        args_text = " ".join(parsed_command["args"])
                        command_text += f" {args_text}"
                    
                    suggestions.append({
                        "command": command_text,
                        "description": f"AI suggestion based on your query: '{query}'",
                        "type": "ai_suggestion",
                        "confidence": parsed_command.get("confidence", 0.9)
                    })
                    
                    similar_commands = find_similar_commands(cmd, all_commands)
                    for similar_cmd in similar_commands[:2]:
                        suggestions.append({
                            "command": similar_cmd,
                            "description": all_commands.get(similar_cmd, {}).get("description", ""),
                            "type": "ai_alternative",
                            "confidence": 0.7
                        })
            except Exception as e:
                logger.warning(f"Error using AI for command suggestions: {str(e)}")
        
        if query:
            for cmd, desc in all_commands.items():
                if cmd.lower().startswith(query):
                    suggestions.append({
                        "command": cmd,
                        "description": desc.get("description", "") if isinstance(desc, dict) else desc,
                        "type": "main"
                    })
                    
            for agent_name in ["vscode", "security", "sysadmin", "coder", "researcher", "database", "devops"]:
                if agent_name.lower().startswith(query):
                    suggestions.append({
                        "command": agent_name,
                        "description": f"{agent_name.capitalize()} agent commands",
                        "type": "agent"
                    })
                elif query.startswith(agent_name + " ") or query == agent_name:
                    agent_query = query[len(agent_name):].strip()
                    
                    agent = getattr(command_center.commander, f"{agent_name}_agent", None)
                    if agent:
                        agent_commands = agent.get_commands()
                        for cmd, desc in agent_commands.items():
                            if not agent_query or cmd.lower().startswith(agent_query):
                                suggestions.append({
                                    "command": f"{agent_name} {cmd}",
                                    "description": desc.get("description", "") if isinstance(desc, dict) else desc,
                                    "type": "subcommand"
                                })
            
            if query.startswith("file "):
                file_options = ["list", "read", "write", "create", "delete"]
                file_query = query[5:].strip()
                for opt in file_options:
                    if not file_query or opt.startswith(file_query):
                        suggestions.append({
                            "command": f"file {opt}",
                            "description": f"File operation: {opt}",
                            "type": "subcommand"
                        })
                        
            if query.startswith("terminal "):
                linux_commands = [
                    "ls", "cd", "mkdir", "rm", "cp", "mv", "cat", "grep",
                    "find", "ps", "top", "df", "du", "ssh", "scp"
                ]
                terminal_query = query[9:].strip()
                for cmd in linux_commands:
                    if not terminal_query or cmd.startswith(terminal_query):
                        suggestions.append({
                            "command": f"terminal {cmd}",
                            "description": f"Execute Linux command: {cmd}",
                            "type": "subcommand"
                        })
        else:
            main_commands = ["help", "file", "terminal", "about"]
            for cmd in main_commands:
                cmd_info = all_commands.get(cmd, {})
                suggestions.append({
                    "command": cmd,
                    "description": cmd_info.get("description", "") if isinstance(cmd_info, dict) else cmd_info,
                    "type": "main"
                })
            
            for agent in ["vscode", "security", "sysadmin", "coder"]:
                suggestions.append({
                    "command": agent,
                    "description": f"{agent.capitalize()} agent commands",
                    "type": "agent"
                })
        
        def sort_key(item):
            type_order = {"ai_suggestion": -1, "ai_alternative": 0, "main": 1, "agent": 2, "subcommand": 3}
            return (type_order.get(item["type"], 4), item["command"])
            
        suggestions.sort(key=sort_key)
        
        unique_suggestions = []
        seen_commands = set()
        for suggestion in suggestions:
            if suggestion["command"] not in seen_commands:
                unique_suggestions.append(suggestion)
                seen_commands.add(suggestion["command"])
        
        unique_suggestions = unique_suggestions[:10]
        
        return jsonify({"status": "success", "suggestions": unique_suggestions})
    except Exception as e:
        logger.error(f"Error getting command suggestions: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        image_data = data.get('image_data')
        query = data.get('query')
        
        if not image_data:
            return jsonify({"status": "error", "message": "Missing image_data parameter"}), 400
            
        workflow_data = {
            'image_data': image_data,
            'query': query,
            'store_in_memory': data.get('store_in_memory', False)
        }
        
        result = command_center.agent_to_agent('commander', 'commander', 'analyze_image', workflow_data)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({"status": "error", "message": "Missing prompt parameter"}), 400
            
        workflow_data = {
            'prompt': prompt,
            'store_in_memory': data.get('store_in_memory', False)
        }
        
        result = command_center.agent_to_agent('commander', 'commander', 'generate_image', workflow_data)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
@app.route('/code-review', methods=['POST'])
def visual_code_review():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        code = data.get('code')
        language = data.get('language', 'python')
        screenshot = data.get('screenshot')
        security_focus = data.get('security_focus', False)
        
        if not code:
            return jsonify({"status": "error", "message": "Missing code parameter"}), 400
            
        workflow_data = {
            'code': code,
            'language': language,
            'screenshot': screenshot,
            'security_focus': security_focus
        }
        
        result = command_center.agent_to_agent('commander', 'commander', 'visual_code_review', workflow_data)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
@app.route('/research', methods=['POST'])
def research_with_sources():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        query = data.get('query')
        context_urls = data.get('context_urls', [])
        
        if not query:
            return jsonify({"status": "error", "message": "Missing query parameter"}), 400
            
        workflow_data = {
            'query': query,
            'context_urls': context_urls,
            'store_in_memory': data.get('store_in_memory', False)
        }
        
        result = command_center.agent_to_agent('commander', 'commander', 'research_with_sources', workflow_data)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
@app.route('/knowledge', methods=['POST'])
def knowledge_store():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        action = data.get('action')
        
        if not action:
            return jsonify({"status": "error", "message": "Missing action parameter"}), 400
            
        if action == 'store' and (not data.get('key') or not data.get('content')):
            return jsonify({"status": "error", "message": "Store action requires key and content parameters"}), 400
            
        if action == 'retrieve' and not data.get('key'):
            return jsonify({"status": "error", "message": "Retrieve action requires key parameter"}), 400
            
        if action == 'search' and not data.get('query'):
            return jsonify({"status": "error", "message": "Search action requires query parameter"}), 400
            
        result = command_center.agent_to_agent('commander', 'commander', 'knowledge_store', data)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/proxy-image')
def proxy_image():
    try:
        url = request.args.get('url')
        if not url:
            return jsonify({"status": "error", "message": "No URL provided"}), 400
            
        response = requests.get(url)
        if response.status_code != 200:
            return jsonify({"status": "error", "message": f"Failed to fetch image: {response.status_code}"}), response.status_code
            
        img_io = BytesIO(response.content)
        
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        
        return send_file(img_io, mimetype=content_type)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/task-templates')
def get_task_templates():
    try:
        templates = task_service.get_task_templates()
        return jsonify({"status": "success", "templates": templates})
    except Exception as e:
        logger.error(f"Error getting task templates: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/task-template/<template_id>')
def get_task_template(template_id):
    try:
        template = task_service.get_task_template(template_id)
        if not template:
            return jsonify({"status": "error", "message": f"Template '{template_id}' not found"}), 404
            
        return jsonify({"status": "success", "template": template})
    except Exception as e:
        logger.error(f"Error getting task template: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/task-suggestions')
def get_task_suggestions():
    try:
        query = request.args.get('query', '')
        if not query:
            return jsonify({"status": "error", "message": "No query provided"}), 400
            
        suggestions = task_service.get_task_suggestions(query)
        
        if suggestions:
            top_suggestion = suggestions[0]
            steps = task_service.get_task_steps(top_suggestion["id"])
            top_suggestion["steps"] = steps
            
            ai_suggestions = task_service.get_ai_suggestions(top_suggestion["id"])
            top_suggestion["ai_suggestions"] = ai_suggestions
            
        return jsonify({
            "status": "success", 
            "suggestions": suggestions,
            "missing_ai_services": task_service.get_missing_ai_services()
        })
    except Exception as e:
        logger.error(f"Error getting task suggestions: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/task-steps/<template_id>')
def get_task_steps(template_id):
    try:
        steps = task_service.get_task_steps(template_id)
        if not steps:
            return jsonify({"status": "error", "message": f"No steps found for template '{template_id}'"}), 404
            
        return jsonify({
            "status": "success", 
            "steps": steps,
            "ai_suggestions": task_service.get_ai_suggestions(template_id)
        })
    except Exception as e:
        logger.error(f"Error getting task steps: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/available-ai-services')
def get_available_ai_services():
    try:
        available = task_service._get_available_ai()
        missing = task_service.get_missing_ai_services()
        
        return jsonify({
            "status": "success",
            "available_services": available,
            "missing_services": missing
        })
    except Exception as e:
        logger.error(f"Error getting AI service info: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
