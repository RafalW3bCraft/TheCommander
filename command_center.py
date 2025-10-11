import logging
import json
import os
from typing import Dict, List, Any, Optional, Union
from agent import Commander

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CommandCenter:
    
    def __init__(self):
        logger.debug("Initializing Command Center")
        
        self.commander = Commander()
        
        self.coder = self.commander.coder_agent
        self.researcher = self.commander.researcher_agent
        self.sysadmin = self.commander.sysadmin_agent
        self.memory = self.commander.memorykeeper_agent
        self.vscode = self.commander.vscode_agent
        self.security = self.commander.security_agent
        self.database = self.commander.database_agent
        self.devops = self.commander.devops_agent
        self.learning = self.commander.learning_agent
        
        self.task_history = []
    
    def execute_command(self, command_text: str, use_advanced_parsing: bool = True, use_ai: bool = True) -> str:
        logger.debug(f"Command Center executing: {command_text}")
        
        self.task_history.append({
            "command": command_text,
            "timestamp": self._get_timestamp()
        })
        
        try:
            from ai_service import ai_service
            
            result = self.commander.execute_command(
                command_text,
                use_advanced_parsing=use_advanced_parsing,
                use_ai=use_ai,
                ai_service=ai_service
            )
        except ImportError:
            logger.warning("AI service not available, falling back to basic parsing")
            result = self.commander.execute_command(command_text, use_advanced_parsing=True, use_ai=False)
        except Exception as e:
            logger.error(f"Error executing command with advanced parsing: {str(e)}")
            result = self.commander.execute_command(command_text, use_advanced_parsing=False, use_ai=False)
        
        self.task_history[-1]["result"] = result[:100] + "..." if len(result) > 100 else result
        
        return result
    
    def agent_to_agent(self, source_agent: str, target_agent: str, 
                        action: str, data: Any) -> Dict[str, Any]:
        logger.debug(f"Agent-to-agent call: {source_agent} -> {target_agent} [{action}]")
        
        try:
            agents = {
                "commander": self.commander,
                "coder": self.coder,
                "researcher": self.researcher,
                "sysadmin": self.sysadmin,
                "memory": self.memory,
                "vscode": self.vscode,
                "security": self.security,
                "database": self.database,
                "devops": self.devops,
                "learning": self.learning
            }
            
            if source_agent not in agents:
                return {"error": f"Unknown source agent: {source_agent}"}
            
            if target_agent not in agents:
                return {"error": f"Unknown target agent: {target_agent}"}
            
            if action == "research_and_code":
                return self._workflow_research_and_code(data)
            
            elif action == "research_and_remember":
                return self._workflow_research_and_remember(data)
            
            elif action == "code_and_execute":
                return self._workflow_code_and_execute(data)
                
            elif action == "vscode_project_setup":
                return self._workflow_vscode_project_setup(data)
                
            elif action == "secure_database_setup":
                return self._workflow_secure_database_setup(data)
                
            elif action == "analyze_and_improve":
                return self._workflow_analyze_and_improve(data)
                
            elif action == "analyze_image":
                return self._workflow_analyze_image(data)
                
            elif action == "generate_image":
                return self._workflow_generate_image(data)
                
            elif action == "visual_code_review":
                return self._workflow_visual_code_review(data)
                
            elif action == "research_with_sources":
                return self._workflow_research_with_sources(data)
                
            elif action == "knowledge_store":
                return self._workflow_knowledge_store(data)
            
            elif target_agent == "coder":
                if action in self.coder.get_commands():
                    args = data.get("args", [])
                    result = self.coder.execute(action, args)
                    return {"result": result}
                else:
                    return {"error": f"Unknown coder action: {action}"}
            
            elif target_agent == "researcher":
                if action in self.researcher.get_commands():
                    args = data.get("args", [])
                    result = self.researcher.execute(action, args)
                    return {"result": result}
                else:
                    return {"error": f"Unknown researcher action: {action}"}
            
            elif target_agent == "sysadmin":
                if action in self.sysadmin.get_commands():
                    args = data.get("args", [])
                    result = self.sysadmin.execute(action, args)
                    return {"result": result}
                else:
                    return {"error": f"Unknown sysadmin action: {action}"}
            
            elif target_agent == "memory":
                if action in self.memory.get_commands():
                    args = data.get("args", [])
                    result = self.memory.execute(action, args)
                    return {"result": result}
                else:
                    return {"error": f"Unknown memory action: {action}"}
            
            elif target_agent == "vscode":
                if action in self.vscode.get_commands():
                    args = data.get("args", [])
                    result = self.vscode.execute(action, args)
                    return {"result": result}
                else:
                    return {"error": f"Unknown vscode action: {action}"}
                    
            elif target_agent == "security":
                if action in self.security.get_commands():
                    args = data.get("args", [])
                    result = self.security.execute(action, args)
                    return {"result": result}
                else:
                    return {"error": f"Unknown security action: {action}"}
                    
            elif target_agent == "database":
                if action in self.database.get_commands():
                    args = data.get("args", [])
                    result = self.database.execute(action, args)
                    return {"result": result}
                else:
                    return {"error": f"Unknown database action: {action}"}
                    
            elif target_agent == "devops":
                if action in self.devops.get_commands():
                    args = data.get("args", [])
                    result = self.devops.execute(action, args)
                    return {"result": result}
                else:
                    return {"error": f"Unknown devops action: {action}"}
                    
            elif target_agent == "learning":
                if action in self.learning.get_commands():
                    args = data.get("args", [])
                    result = self.learning.execute(action, args)
                    return {"result": result}
                else:
                    return {"error": f"Unknown learning action: {action}"}
            
            else:
                return {"error": f"Unsupported action: {action}"}
                
        except Exception as e:
            logger.error(f"Error in agent-to-agent communication: {str(e)}")
            return {"error": f"Error in agent-to-agent communication: {str(e)}"}
    
    def _workflow_research_and_code(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            query = data.get("query")
            language = data.get("language", "python")
            
            if not query:
                return {"error": "Missing query parameter"}
            
            logger.debug(f"Researching: {query}")
            research_result = self.researcher.execute("summarize", [query])
            
            logger.debug(f"Generating code based on research in {language}")
            code_request = f"Code to implement: {query} based on: {research_result[:500]}"
            code_result = self.coder.execute("write", [language, code_request])
            
            memory_key = f"research_code_{self._generate_key(query)}"
            self.memory.execute("remember", [memory_key, json.dumps({
                "query": query,
                "research": research_result[:1000],
                "code": code_result,
                "language": language
            }), "research_code"])
            
            return {
                "research": research_result,
                "code": code_result,
                "memory_key": memory_key
            }
            
        except Exception as e:
            logger.error(f"Error in research_and_code workflow: {str(e)}")
            return {"error": f"Error in research_and_code workflow: {str(e)}"}
    
    def _workflow_research_and_remember(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            query = data.get("query")
            category = data.get("category", "research")
            
            if not query:
                return {"error": "Missing query parameter"}
            
            logger.debug(f"Researching for memory: {query}")
            if self._is_url(query):
                research_result = self.researcher.execute("scrape", [query])
            else:
                research_result = self.researcher.execute("summarize", [query])
            
            analysis_result = self.researcher.execute("analyze", [research_result[:2000]])
            
            memory_key = f"research_{self._generate_key(query)}"
            memory_value = json.dumps({
                "query": query,
                "content": research_result[:2000],
                "analysis": analysis_result
            })
            
            self.memory.execute("remember", [memory_key, memory_value, category])
            
            return {
                "research": research_result[:500] + "...",
                "analysis": analysis_result,
                "memory_key": memory_key,
                "category": category
            }
            
        except Exception as e:
            logger.error(f"Error in research_and_remember workflow: {str(e)}")
            return {"error": f"Error in research_and_remember workflow: {str(e)}"}
    
    def _workflow_code_and_execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            description = data.get("description")
            language = data.get("language", "python")
            
            if not description:
                return {"error": "Missing description parameter"}
            
            logger.debug(f"Generating {language} code for: {description}")
            code_result = self.coder.execute("write", [language, description])
            
            import re
            code_match = re.search(r'```(?:\w+)?\n(.*?)```', code_result, re.DOTALL)
            if code_match:
                code = code_match.group(1)
            else:
                code = code_result
            
            if language.lower() == "python":
                logger.debug("Executing generated Python code")
                execution_result = self.coder.execute("run", [language, code])
            else:
                execution_result = f"Code execution is only supported for Python. Generated {language} code but did not execute it."
            
            memory_key = f"code_{language}_{self._generate_key(description)}"
            self.memory.execute("remember", [memory_key, json.dumps({
                "description": description,
                "code": code,
                "execution_result": execution_result,
                "language": language
            }), "code_executions"])
            
            return {
                "code": code_result,
                "execution": execution_result,
                "memory_key": memory_key
            }
            
        except Exception as e:
            logger.error(f"Error in code_and_execute workflow: {str(e)}")
            return {"error": f"Error in code_and_execute workflow: {str(e)}"}
    
    def get_task_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.task_history[-limit:] if limit > 0 else self.task_history
    
    def _is_url(self, text: str) -> bool:
        return text.startswith(("http://", "https://"))
    
    def _generate_key(self, text: str) -> str:
        import re
        key = re.sub(r'[^\w]', '_', text.lower())
        key = re.sub(r'_+', '_', key)
        return key[:50]
    
    def _workflow_vscode_project_setup(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            project_type = data.get("project_type", "python")
            project_name = data.get("project_name", "my_project")
            
            if not project_type:
                return {"error": "Missing project_type parameter"}
            
            logger.debug(f"Getting recommended extensions for {project_type}")
            extensions_result = self.vscode.execute("recommend-extensions", [project_type])
            
            logger.debug(f"Creating launch configuration for {project_type}")
            launch_config_name = f"Debug {project_type.capitalize()}"
            
            if project_type.lower() == "python":
                program_path = "app.py"
                launch_result = self.vscode.execute("create-launch", [launch_config_name, "python", program_path])
            elif project_type.lower() in ["node", "javascript", "typescript"]:
                program_path = "index.js"
                launch_result = self.vscode.execute("create-launch", [launch_config_name, "node", program_path])
            else:
                launch_result = f"No predefined launch configuration for {project_type}. Created generic configuration."
                
            logger.debug(f"Creating common tasks for {project_type}")
            if project_type.lower() == "python":
                build_task = self.vscode.execute("create-task", ["test", "python -m pytest"])
                run_task = self.vscode.execute("create-task", ["run", "python app.py"])
            elif project_type.lower() in ["node", "javascript", "typescript"]:
                build_task = self.vscode.execute("create-task", ["build", "npm run build"])
                run_task = self.vscode.execute("create-task", ["start", "npm start"])
            else:
                build_task = self.vscode.execute("create-task", ["build", f"echo 'Building {project_name}...'"])
                run_task = self.vscode.execute("create-task", ["run", f"echo 'Running {project_name}...'"])
                
            terminal_result = self.vscode.execute("linux-terminal", ["bash", "/bin/bash"])
            
            memory_key = f"vscode_project_{self._generate_key(project_name)}"
            self.memory.execute("remember", [memory_key, json.dumps({
                "project_type": project_type,
                "project_name": project_name,
                "extensions": extensions_result,
                "launch_config": launch_result,
                "tasks": {
                    "build": build_task,
                    "run": run_task
                },
                "terminal": terminal_result
            }), "vscode_projects"])
            
            return {
                "project_name": project_name,
                "project_type": project_type,
                "extensions": extensions_result,
                "launch_config": launch_result,
                "tasks": {
                    "build": build_task, 
                    "run": run_task
                },
                "terminal": terminal_result,
                "memory_key": memory_key
            }
            
        except Exception as e:
            logger.error(f"Error in vscode_project_setup workflow: {str(e)}")
            return {"error": f"Error in vscode_project_setup workflow: {str(e)}"}
    
    def _workflow_secure_database_setup(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            db_type = data.get("db_type", "postgresql")
            description = data.get("description")
            
            if not description:
                return {"error": "Missing database description parameter"}
            
            logger.debug(f"Generating {db_type} schema for: {description}")
            schema_result = self.database.execute("generate-schema", [db_type, description])
            
            logger.debug("Performing security audit on the schema")
            security_audit = self.security.execute("security-audit", [db_type, schema_result])
            
            logger.debug(f"Generating deployment configuration for {db_type}")
            deployment_config = self.devops.execute("deployment", ["kubernetes", f"{db_type}-database"])
            
            memory_key = f"db_setup_{self._generate_key(description)}"
            self.memory.execute("remember", [memory_key, json.dumps({
                "db_type": db_type,
                "description": description,
                "schema": schema_result,
                "security_audit": security_audit,
                "deployment_config": deployment_config
            }), "database_setups"])
            
            return {
                "schema": schema_result,
                "security_audit": security_audit,
                "deployment_config": deployment_config,
                "memory_key": memory_key
            }
            
        except Exception as e:
            logger.error(f"Error in secure_database_setup workflow: {str(e)}")
            return {"error": f"Error in secure_database_setup workflow: {str(e)}"}
    
    def _workflow_analyze_and_improve(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            code = data.get("code")
            language = data.get("language", "python")
            
            if not code:
                return {"error": "Missing code parameter"}
            
            logger.debug(f"Analyzing {language} code for improvements")
            security_analysis = self.security.execute("scan-code-text", [language, code])
            
            from ai_service import ai_service
            improvement_suggestions = ai_service.suggest_improvements(language, code)
            
            memory_key = f"code_analysis_{self._generate_key(code[:50])}"
            self.memory.execute("remember", [memory_key, json.dumps({
                "language": language,
                "code_snippet": code[:200],
                "security_analysis": security_analysis[:500],
                "improvement_suggestions": improvement_suggestions[:500]
            }), "code_analyses"])
            
            return {
                "security_analysis": security_analysis,
                "improvement_suggestions": improvement_suggestions,
                "memory_key": memory_key
            }
            
        except Exception as e:
            logger.error(f"Error in analyze_and_improve workflow: {str(e)}")
            return {"error": f"Error in analyze_and_improve workflow: {str(e)}"}
    
    def _workflow_analyze_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            image_data = data.get("image_data")
            query = data.get("query", "Describe this image in detail")
            store_in_memory = data.get("store_in_memory", False)
            
            if not image_data:
                return {"error": "Missing image_data parameter"}
            
            logger.debug("Analyzing image with AI")
            from ai_service import ai_service
            analysis_result = ai_service.analyze_image(image_data, query)
            
            if store_in_memory:
                memory_key = f"image_analysis_{self._generate_key(query)}"
                self.memory.execute("remember", [memory_key, json.dumps({
                    "query": query,
                    "analysis": analysis_result[:1000]
                }), "image_analyses"])
                
                return {
                    "analysis": analysis_result,
                    "memory_key": memory_key
                }
            
            return {"analysis": analysis_result}
            
        except Exception as e:
            logger.error(f"Error in analyze_image workflow: {str(e)}")
            return {"error": f"Error in analyze_image workflow: {str(e)}"}
    
    def _workflow_generate_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = data.get("prompt")
            store_in_memory = data.get("store_in_memory", False)
            
            if not prompt:
                return {"error": "Missing prompt parameter"}
            
            logger.debug(f"Generating image with prompt: {prompt}")
            from ai_service import ai_service
            generation_result = ai_service.generate_image(prompt)
            
            if store_in_memory and isinstance(generation_result, dict):
                memory_key = f"generated_image_{self._generate_key(prompt)}"
                self.memory.execute("remember", [memory_key, json.dumps({
                    "prompt": prompt,
                    "image_url": generation_result.get("url", "")
                }), "generated_images"])
                
                return {
                    "image_url": generation_result.get("url"),
                    "memory_key": memory_key
                }
            
            return generation_result
            
        except Exception as e:
            logger.error(f"Error in generate_image workflow: {str(e)}")
            return {"error": f"Error in generate_image workflow: {str(e)}"}
    
    def _workflow_visual_code_review(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            code = data.get("code")
            language = data.get("language", "python")
            screenshot = data.get("screenshot")
            security_focus = data.get("security_focus", False)
            
            if not code:
                return {"error": "Missing code parameter"}
            
            logger.debug(f"Performing visual code review for {language}")
            
            from ai_service import ai_service
            
            if security_focus:
                analysis_result = ai_service.analyze_code(language, code, analysis_type="security")
            else:
                analysis_result = ai_service.suggest_improvements(language, code)
            
            if screenshot:
                logger.debug("Analyzing screenshot with the code")
                screenshot_analysis = ai_service.analyze_image(screenshot, 
                    f"This is a screenshot of code. Please analyze it in the context of: {code[:200]}")
                
                return {
                    "code_analysis": analysis_result,
                    "screenshot_analysis": screenshot_analysis
                }
            
            return {"code_analysis": analysis_result}
            
        except Exception as e:
            logger.error(f"Error in visual_code_review workflow: {str(e)}")
            return {"error": f"Error in visual_code_review workflow: {str(e)}"}
    
    def _workflow_research_with_sources(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            query = data.get("query")
            context_urls = data.get("context_urls", [])
            store_in_memory = data.get("store_in_memory", False)
            
            if not query:
                return {"error": "Missing query parameter"}
            
            logger.debug(f"Researching with sources: {query}")
            
            context_sources = []
            for url in context_urls:
                try:
                    scraped_content = self.researcher.execute("scrape", [url])
                    context_sources.append({
                        "title": url,
                        "content": scraped_content[:2000]
                    })
                except Exception as scrape_err:
                    logger.warning(f"Failed to scrape {url}: {str(scrape_err)}")
            
            from ai_service import ai_service
            answer_result = ai_service.answer_with_sources(query, context_sources)
            
            if store_in_memory:
                memory_key = f"research_{self._generate_key(query)}"
                self.memory.execute("remember", [memory_key, json.dumps({
                    "query": query,
                    "sources": [s["title"] for s in context_sources],
                    "answer": answer_result[:1000]
                }), "research_with_sources"])
                
                return {
                    "answer": answer_result,
                    "sources": context_sources,
                    "memory_key": memory_key
                }
            
            return {
                "answer": answer_result,
                "sources": context_sources
            }
            
        except Exception as e:
            logger.error(f"Error in research_with_sources workflow: {str(e)}")
            return {"error": f"Error in research_with_sources workflow: {str(e)}"}
    
    def _workflow_knowledge_store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            action = data.get("action")
            
            if not action:
                return {"error": "Missing action parameter"}
            
            from ai_service import ai_service
            
            if action == "store":
                key = data.get("key")
                content = data.get("content")
                metadata = data.get("metadata", {})
                
                if not key or not content:
                    return {"error": "Missing key or content for store action"}
                
                logger.debug(f"Storing knowledge: {key}")
                result = ai_service.store_knowledge(key, content, metadata)
                return {"result": result}
            
            elif action == "retrieve":
                key = data.get("key")
                
                if not key:
                    return {"error": "Missing key for retrieve action"}
                
                logger.debug(f"Retrieving knowledge: {key}")
                result = ai_service.retrieve_knowledge(key)
                return {"result": result}
            
            elif action == "search":
                query = data.get("query")
                
                if not query:
                    return {"error": "Missing query for search action"}
                
                logger.debug(f"Searching knowledge: {query}")
                result = ai_service.search_knowledge(query)
                return {"result": result}
            
            else:
                return {"error": f"Unknown action: {action}"}
            
        except Exception as e:
            logger.error(f"Error in knowledge_store workflow: {str(e)}")
            return {"error": f"Error in knowledge_store workflow: {str(e)}"}
    
    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().isoformat()

command_center = CommandCenter()
