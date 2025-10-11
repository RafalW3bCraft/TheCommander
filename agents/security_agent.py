import os
import re
import subprocess
import logging
import json
import requests
from typing import List, Dict, Any, Optional
from agents.base_agent import BaseAgent
from ai_service import ai_service

logger = logging.getLogger(__name__)

class SecurityAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="SecurityAgent",
            description="Specialized in vulnerability detection and security analysis."
        )
        self.supported_scan_types = [
            "code", "web", "deps", "system", "network"
        ]

    def get_commands(self):
        return {
            "scan-code": {
                "description": "Scan code for security vulnerabilities",
                "usage": "scan-code <file_path>",
                "examples": [
                    "scan-code main.py",
                    "scan-code ./webapp/auth.js"
                ]
            },
            "owasp-check": {
                "description": "Check a web application against OWASP Top 10 vulnerabilities",
                "usage": "owasp-check <target_url>",
                "examples": [
                    "owasp-check example.com",
                    "owasp-check https://myapp.com/login"
                ]
            },
            "check-deps": {
                "description": "Check project dependencies for known vulnerabilities",
                "usage": "check-deps <project_path>",
                "examples": [
                    "check-deps ./",
                    "check-deps ./myproject/package.json"
                ]
            },
            "harden-linux": {
                "description": "Get recommendations for hardening a Linux system",
                "usage": "harden-linux [specific_area]",
                "examples": [
                    "harden-linux",
                    "harden-linux ssh",
                    "harden-linux firewall"
                ]
            },
            "generate-report": {
                "description": "Generate a security report for a target",
                "usage": "generate-report <target> [vuln_type]",
                "examples": [
                    "generate-report myapp.com",
                    "generate-report myapp.com xss",
                    "generate-report ./src sql-injection"
                ]
            }
        }

    def execute(self, command, args):
        try:
            if command == "scan-code":
                if not args:
                    return "Error: Missing file path. Usage: scan-code <file_path>"
                return self._scan_code(args[0])

            elif command == "owasp-check":
                if not args:
                    return "Error: Missing target URL. Usage: owasp-check <target_url>"
                return self._owasp_check(args[0])

            elif command == "check-deps":
                path = "./" if not args else args[0]
                return self._check_dependencies(path)

            elif command == "harden-linux":
                area = None if not args else args[0]
                return self._harden_linux(area)

            elif command == "generate-report":
                if not args:
                    return "Error: Missing target. Usage: generate-report <target> [vuln_type]"

                target = args[0]
                vuln_type = args[1] if len(args) > 1 else None
                return self._generate_report(target, vuln_type)

            else:
                return f"Unknown command: '{command}'"

        except Exception as e:
            logger.error(f"Error in SecurityAgent: {str(e)}")
            return f"Error executing command: {str(e)}"

    def _scan_code(self, file_path):
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        try:
            with open(file_path, 'r') as f:
                code = f.read()

            _, ext = os.path.splitext(file_path)
            language = self._get_language_from_extension(ext)

            if not language:
                return f"Error: Unsupported file type: {ext}"

            try:
                logger.debug(f"Using AI Service to scan {language} code for security issues")
                ai_analysis = ai_service.analyze_code(language, code, analysis_type="security")

                if ai_analysis and "Error" not in ai_analysis:
                    result = f"Security Scan Results for {file_path} ({language}):\n\n"
                    result += ai_analysis
                    return result
            except Exception as ai_err:
                logger.warning(f"AI Service code security scan failed: {str(ai_err)}. Falling back to pattern-based scanning.")

            vulnerabilities = []

            if language in ["python", "py"]:
                vulnerabilities.extend(self._check_python_vulnerabilities(code))
            elif language in ["javascript", "js"]:
                vulnerabilities.extend(self._check_javascript_vulnerabilities(code))
            elif language in ["php"]:
                vulnerabilities.extend(self._check_php_vulnerabilities(code))

            if vulnerabilities:
                result = f"Security Scan Results for {file_path} ({language}):\n\n"
                result += "Potential Vulnerabilities Found:\n"
                for i, vuln in enumerate(vulnerabilities, 1):
                    result += f"{i}. {vuln['type']}: {vuln['description']}\n"
                    if 'line' in vuln:
                        result += f"   Line {vuln['line']}: {vuln['code']}\n"
                    if 'recommendation' in vuln:
                        result += f"   Recommendation: {vuln['recommendation']}\n"
                    result += "\n"
            else:
                result = f"Security Scan Results for {file_path} ({language}):\n\n"
                result += "No obvious security vulnerabilities detected. However, this does not guarantee the code is secure.\n"
                result += "Consider a more thorough security review with specialized tools."

            return result

        except Exception as e:
            logger.error(f"Error scanning code: {str(e)}")
            return f"Error scanning code: {str(e)}"

    def _owasp_check(self, target_url):
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        try:
            system_prompt = f"""You are a security expert specializing in web application security.
Analyze the target URL {target_url} and provide a thorough OWASP Top 10 security assessment.
Focus on the most critical security risks from the latest OWASP Top 10:

1. Broken Access Control
2. Cryptographic Failures
3. Injection
4. Insecure Design
5. Security Misconfiguration
6. Vulnerable and Outdated Components
7. Identification and Authentication Failures
8. Software and Data Integrity Failures
9. Security Logging and Monitoring Failures
10. Server-Side Request Forgery

For each risk category, explain:
- What the vulnerability is
- How it might manifest in this application
- How to test for it
- Recommendations to mitigate the risk

Format your response in clear sections with headings and bullet points."""

            if 'claude' in ai_service.models:
                logger.debug(f"Using AI Service for OWASP check of {target_url}")
                response = ai_service.models['claude'].messages.create(
                    model="claude-3-5-sonnet-20241022",
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": f"Perform an OWASP Top 10 security assessment for {target_url}"}
                    ],
                    temperature=0.1,
                    max_tokens=3000
                )
                result = f"OWASP Top 10 Security Assessment for {target_url}\n\n"
                result += response.content[0].text
                return result
            else:
                return f"Error: AI service not available. Manual OWASP assessment recommended for {target_url}"

        except Exception as e:
            logger.error(f"Error performing OWASP check: {str(e)}")
            return f"Error performing OWASP check: {str(e)}"

    def _check_dependencies(self, project_path):
        project_type = self._detect_project_type(project_path)

        if not project_type:
            return f"Error: Could not determine project type for {project_path}"

        try:
            dependencies = self._extract_dependencies(project_path, project_type)

            if not dependencies:
                return f"No dependencies found in {project_path}"

            system_prompt = """You are a security expert specializing in software supply chain security.
Analyze the provided dependencies for potential security vulnerabilities and outdated packages.
For each dependency, consider:

1. Known vulnerabilities in current versions
2. Whether the version is outdated
3. The likelihood of security issues based on the package's track record
4. Proper dependency management practices

Format your response in clear sections with headings and bullet points."""

            dep_list = "\n".join([f"{name}: {version}" for name, version in dependencies.items()])

            if 'claude' in ai_service.models:
                logger.debug(f"Using AI Service for dependency check")
                response = ai_service.models['claude'].messages.create(
                    model="claude-3-5-sonnet-20241022",
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": f"Analyze these {project_type} dependencies for security issues:\n\n{dep_list}"}
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                result = f"Dependency Security Check for {project_path} ({project_type}):\n\n"
                result += response.content[0].text
                return result
            else:
                result = f"Dependency Security Check for {project_path} ({project_type}):\n\n"
                result += f"Found {len(dependencies)} dependencies:\n"
                for name, version in dependencies.items():
                    result += f"- {name}: {version}\n"
                result += "\nNote: AI service not available for detailed vulnerability analysis."
                return result

        except Exception as e:
            logger.error(f"Error checking dependencies: {str(e)}")
            return f"Error checking dependencies: {str(e)}"

    def _harden_linux(self, area):
        try:
            focus = f"focusing on {area}" if area else "covering all major areas"
            system_prompt = """You are a Linux security expert specializing in system hardening.
Provide detailed, actionable recommendations for hardening Linux systems.
Focus on:

1. Practical steps that can be implemented
2. Command examples where applicable
3. Configuration file changes with specific parameters
4. Best practices from established security frameworks

Format your response in clear sections with headings, numbered steps, and code examples."""

            if 'claude' in ai_service.models:
                logger.debug(f"Using AI Service for Linux hardening recommendations")
                response = ai_service.models['claude'].messages.create(
                    model="claude-3-5-sonnet-20241022",
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": f"Provide Linux hardening recommendations {focus}"}
                    ],
                    temperature=0.1,
                    max_tokens=2500
                )
                result = f"Linux Hardening Recommendations"
                if area:
                    result += f" - {area.upper()}"
                result += "\n\n"
                result += response.content[0].text
                return result
            else:
                result = f"Linux Hardening Recommendations"
                if area:
                    result += f" - {area.upper()}"
                result += "\n\n"
                result += "Error: AI service not available. Please consult security hardening guides manually."
                return result

        except Exception as e:
            logger.error(f"Error generating hardening recommendations: {str(e)}")
            return f"Error generating hardening recommendations: {str(e)}"

    def _generate_report(self, target, vuln_type):
        try:
            is_url = target.startswith(("http://", "https://", "www."))

            if is_url:
                system_prompt = f"""You are a security expert specializing in web application security.
Generate a comprehensive security report for the target website {target}.
Include in your report:

1. Executive summary
2. Methodology
3. Findings and vulnerabilities
4. Risk assessment for each finding
5. Detailed recommendations
6. Remediation plan with priorities

Format your report professionally with clear sections, headings, and bullet points."""
                user_message = f"Generate a comprehensive security report for {target}"
                if vuln_type:
                    user_message += f", focusing on {vuln_type} vulnerabilities"
            else:
                system_prompt = f"""You are a security expert specializing in application security and code review.
Generate a comprehensive security report for the code located at {target}.
Include in your report:

1. Executive summary
2. Methodology for code review
3. Findings and vulnerabilities
4. Risk assessment for each finding
5. Code examples and fix recommendations
6. Remediation plan with priorities

Format your report professionally with clear sections, headings, and bullet points."""
                user_message = f"Generate a comprehensive security report for code at {target}"
                if vuln_type:
                    user_message += f", focusing on {vuln_type} vulnerabilities"

            if 'claude' in ai_service.models:
                logger.debug(f"Using AI Service to generate security report")
                response = ai_service.models['claude'].messages.create(
                    model="claude-3-5-sonnet-20241022",
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.1,
                    max_tokens=3000
                )
                result = f"Security Report for {target}\n\n"
                result += response.content[0].text
                return result
            else:
                return f"Error: AI service not available for report generation on {target}"

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return f"Error generating report: {str(e)}"

    def _get_language_from_extension(self, ext):
        ext = ext.lower()

        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.html': 'html',
            '.css': 'css',
            '.php': 'php',
            '.rb': 'ruby',
            '.java': 'java',
            '.go': 'go',
            '.ts': 'typescript',
            '.cs': 'csharp',
            '.c': 'c',
            '.cpp': 'cpp',
            '.sh': 'bash',
            '.sql': 'sql',
            '.md': 'markdown',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml'
        }

        return language_map.get(ext)

    def _check_python_vulnerabilities(self, code):
        vulnerabilities = []

        sql_patterns = [
            (r'cursor\.execute\s*\(\s*[\'"][^\'",]*%s[^\'",]*[\'"]\s*%\s*\(',
             "Potential SQL Injection",
             "String formatting used with SQL queries is vulnerable to SQL injection attacks.",
             "Use parameterized queries with cursor.execute(query, params) instead of string formatting."),

            (r'cursor\.execute\s*\(\s*[\'"][^\'",]*\'\s*\+',
             "Potential SQL Injection",
             "String concatenation used with SQL queries is vulnerable to SQL injection attacks.",
             "Use parameterized queries with cursor.execute(query, params) instead of string concatenation."),

            (r'cursor\.execute\s*\(\s*f[\'"]',
             "Potential SQL Injection",
             "f-strings used with SQL queries are vulnerable to SQL injection attacks.",
             "Use parameterized queries with cursor.execute(query, params) instead of f-strings.")
        ]

        for pattern, vuln_type, description, recommendation in sql_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                line = code.splitlines()[line_num - 1].strip()
                vulnerabilities.append({
                    'type': vuln_type,
                    'description': description,
                    'line': line_num,
                    'code': line,
                    'recommendation': recommendation
                })

        cmd_patterns = [
            (r'os\.system\s*\(\s*[^)]*\+',
             "Potential Command Injection",
             "String concatenation used with os.system() is vulnerable to command injection attacks.",
             "Use subprocess module with shell=False and pass arguments as a list."),

            (r'os\.system\s*\(\s*f[\'"]',
             "Potential Command Injection",
             "f-strings used with os.system() are vulnerable to command injection attacks.",
             "Use subprocess module with shell=False and pass arguments as a list."),

            (r'subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True',
             "Potential Command Injection",
             "Using shell=True with subprocess functions is vulnerable to command injection attacks.",
             "Use shell=False and pass arguments as a list.")
        ]

        for pattern, vuln_type, description, recommendation in cmd_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                line = code.splitlines()[line_num - 1].strip()
                vulnerabilities.append({
                    'type': vuln_type,
                    'description': description,
                    'line': line_num,
                    'code': line,
                    'recommendation': recommendation
                })

        if 'pickle.loads' in code:
            matches = re.finditer(r'pickle\.loads\s*\(', code)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                line = code.splitlines()[line_num - 1].strip()
                vulnerabilities.append({
                    'type': "Potential Insecure Deserialization",
                    'description': "The pickle module is unsafe when used with untrusted data.",
                    'line': line_num,
                    'code': line,
                    'recommendation': "Avoid using pickle with untrusted data. Consider using JSON or other safer serialization formats."
                })

        secret_patterns = [
            (r'(?:password|passwd|pwd|token|secret|key|api_key|apikey)\s*=\s*[\'"]+[a-zA-Z0-9]{10,}[\'"]+',
             "Potential Hardcoded Secret",
             "Hardcoded secrets found in the code.",
             "Store secrets in environment variables or a secure vault solution.")
        ]

        for pattern, vuln_type, description, recommendation in secret_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                line = code.splitlines()[line_num - 1].strip()
                redacted_line = re.sub(r'([\'"]+)[a-zA-Z0-9]{10,}([\'"]+)', r'\1[REDACTED]\2', line)
                vulnerabilities.append({
                    'type': vuln_type,
                    'description': description,
                    'line': line_num,
                    'code': redacted_line,
                    'recommendation': recommendation
                })

        return vulnerabilities

    def _check_javascript_vulnerabilities(self, code):
        vulnerabilities = []

        xss_patterns = [
            (r'innerHTML\s*=',
             "Potential Cross-Site Scripting (XSS)",
             "Using innerHTML can lead to XSS vulnerabilities if user input is not properly sanitized.",
             "Use textContent instead, or sanitize input with a library like DOMPurify before using innerHTML."),

            (r'document\.write\s*\(',
             "Potential Cross-Site Scripting (XSS)",
             "Using document.write can lead to XSS vulnerabilities if user input is not properly sanitized.",
             "Avoid document.write and use safer DOM manipulation methods."),

            (r'eval\s*\(',
             "Potential Injection and XSS",
             "Using eval() can lead to code injection and XSS vulnerabilities.",
             "Avoid using eval() and find safer alternatives for the intended functionality.")
        ]

        for pattern, vuln_type, description, recommendation in xss_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                line = code.splitlines()[line_num - 1].strip()
                vulnerabilities.append({
                    'type': vuln_type,
                    'description': description,
                    'line': line_num,
                    'code': line,
                    'recommendation': recommendation
                })

        secret_patterns = [
            (r'(?:password|passwd|pwd|token|secret|key|api_key|apikey)\s*=\s*[\'"]+[a-zA-Z0-9]{10,}[\'"]+',
             "Potential Hardcoded Secret",
             "Hardcoded secrets found in the code.",
             "Store secrets in environment variables or a secure vault solution.")
        ]

        for pattern, vuln_type, description, recommendation in secret_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                line = code.splitlines()[line_num - 1].strip()
                redacted_line = re.sub(r'([\'"]+)[a-zA-Z0-9]{10,}([\'"]+)', r'\1[REDACTED]\2', line)
                vulnerabilities.append({
                    'type': vuln_type,
                    'description': description,
                    'line': line_num,
                    'code': redacted_line,
                    'recommendation': recommendation
                })

        return vulnerabilities

    def _check_php_vulnerabilities(self, code):
        vulnerabilities = []

        sql_patterns = [
            (r'mysqli_query\s*\(\s*[^,]+,\s*[\'"][^\'",]*\'\s*\.\s*',
             "Potential SQL Injection",
             "String concatenation used with SQL queries is vulnerable to SQL injection attacks.",
             "Use prepared statements with mysqli_prepare() instead of string concatenation."),

            (r'mysql_query\s*\(\s*[\'"][^\'",]*\'\s*\.\s*',
             "Potential SQL Injection",
             "String concatenation used with mysql_query() is vulnerable to SQL injection attacks.",
             "Use prepared statements with mysqli_prepare() instead of deprecated mysql_query().")
        ]

        for pattern, vuln_type, description, recommendation in sql_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                line = code.splitlines()[line_num - 1].strip()
                vulnerabilities.append({
                    'type': vuln_type,
                    'description': description,
                    'line': line_num,
                    'code': line,
                    'recommendation': recommendation
                })

        cmd_patterns = [
            (r'(?:system|exec|shell_exec|passthru|proc_open)\s*\(\s*[^)]*\.\s*',
             "Potential Command Injection",
             "String concatenation used with command execution functions is vulnerable to command injection attacks.",
             "Avoid using command execution functions with user input, or properly validate and escape inputs.")
        ]

        for pattern, vuln_type, description, recommendation in cmd_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                line = code.splitlines()[line_num - 1].strip()
                vulnerabilities.append({
                    'type': vuln_type,
                    'description': description,
                    'line': line_num,
                    'code': line,
                    'recommendation': recommendation
                })

        if 'echo' in code and not ('htmlspecialchars' in code or 'htmlentities' in code):
            matches = re.finditer(r'echo\s+\$_(?:GET|POST|REQUEST|COOKIE)', code)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                line = code.splitlines()[line_num - 1].strip()
                vulnerabilities.append({
                    'type': "Potential Cross-Site Scripting (XSS)",
                    'description': "Outputting user input without proper escaping can lead to XSS vulnerabilities.",
                    'line': line_num,
                    'code': line,
                    'recommendation': "Use htmlspecialchars() or htmlentities() to escape user input before outputting it."
                })

        return vulnerabilities

    def _detect_project_type(self, project_path):
        if os.path.isfile(project_path):
            if project_path.endswith("package.json"):
                return "nodejs"
            elif project_path.endswith("requirements.txt"):
                return "python"
            elif project_path.endswith("pyproject.toml"):
                return "python"
            return None

        if os.path.isdir(project_path):
            if os.path.exists(os.path.join(project_path, "package.json")):
                return "nodejs"
            elif os.path.exists(os.path.join(project_path, "requirements.txt")):
                return "python"
            elif os.path.exists(os.path.join(project_path, "pyproject.toml")):
                return "python"

        return None

    def _extract_dependencies(self, project_path, project_type):
        dependencies = {}

        if project_type == "nodejs":
            package_json_path = project_path
            if os.path.isdir(project_path):
                package_json_path = os.path.join(project_path, "package.json")

            try:
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)

                if "dependencies" in package_data:
                    for dep, version in package_data["dependencies"].items():
                        dependencies[dep] = version

                if "devDependencies" in package_data:
                    for dep, version in package_data["devDependencies"].items():
                        dependencies[dep] = version
            except Exception as e:
                logger.warning(f"Error parsing package.json: {str(e)}")

        elif project_type == "python":
            if os.path.isdir(project_path):
                requirements_path = os.path.join(project_path, "requirements.txt")
                pyproject_path = os.path.join(project_path, "pyproject.toml")
            else:
                requirements_path = project_path if project_path.endswith("requirements.txt") else None
                pyproject_path = project_path if project_path.endswith("pyproject.toml") else None

            if requirements_path and os.path.exists(requirements_path):
                try:
                    with open(requirements_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                parts = line.split('==')
                                if len(parts) == 2:
                                    dependencies[parts[0]] = parts[1]
                                else:
                                    name = line.split('>=')[0].split('<=')[0].split('~=')[0].split('>')[0].split('<')[0].strip()
                                    version = line.replace(name, '').strip()
                                    if name:
                                        dependencies[name] = version if version else "latest"
                except Exception as e:
                    logger.warning(f"Error parsing requirements.txt: {str(e)}")

            elif pyproject_path and os.path.exists(pyproject_path):
                try:
                    with open(pyproject_path, 'r') as f:
                        content = f.read()

                    in_dependencies = False
                    for line in content.splitlines():
                        line = line.strip()
                        if "[tool.poetry.dependencies]" in line or "[project.dependencies]" in line:
                            in_dependencies = True
                            continue
                        elif in_dependencies and line.startswith('['):
                            in_dependencies = False
                            continue

                        if in_dependencies and '=' in line:
                            parts = line.split('=')
                            if len(parts) >= 2:
                                name = parts[0].strip().strip('"').strip("'")
                                version = parts[1].strip().strip('"').strip("'")
                                if name != "python" and name:
                                    dependencies[name] = version
                except Exception as e:
                    logger.warning(f"Error parsing pyproject.toml: {str(e)}")

        return dependencies
