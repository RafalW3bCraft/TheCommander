# The Commander - AI Agent

This project is a Flask-based AI agent system called "The Commander" that integrates with advanced AI models such as Anthropic Claude and OpenAI to provide natural language understanding, command execution, workflow automation, and more.

## Features

- Natural language command execution with AI-enhanced parsing
- Multi-agent orchestration enabling complex workflows
- Task workflow templates for common security and development tasks
- AI-powered image analysis and generation
- Visual code review with multimodal AI
- Research with cited sources and knowledge management
- Web interface with task selection, help, and command suggestions
- API endpoints for command execution, workflows, and AI services

## Prerequisites

- Python 3.11 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd <Dir>
```

2. (Optional) Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install required Python packages:

```bash
pip install anthropic email-validator flask flask-sqlalchemy gunicorn openai psutil psycopg2-binary requests trafilatura
```

> Note: If you prefer, you can create a `requirements.txt` file with the above dependencies and run `pip install -r requirements.txt`.

## Environment Variables

The application uses the following environment variables:

- `SESSION_SECRET` (optional): Secret key for Flask sessions. Defaults to `"dev-secret-key"` if not set.
- `ANTHROPIC_API_KEY` (required): API key for Anthropic Claude AI integration. You must obtain this key from [Anthropic](https://www.anthropic.com/) and set it in your environment.
- `OPENAI_API_KEY` (optional): API key for OpenAI integration. Obtain from [OpenAI](https://openai.com/) if you want to enable OpenAI features.

Example of setting environment variables on Linux/macOS:

```bash
export SESSION_SECRET="your_secret_key"
export ANTHROPIC_API_KEY="your_anthropic_api_key"
export OPENAI_API_KEY="your_openai_api_key"
```

## Running the Application

To start the Flask web server, run:

```bash
python3 main.py
```

The server will start on `http://0.0.0.0:5000`. You can access the app in your browser at:

```
http://localhost:5000
```

## Usage

- The main interface is available at `/`
- Task workflows can be accessed at `/tasks`
- Help documentation is available at `/help`
- The app provides various API endpoints for command execution, workflows, image analysis, code review, research, and knowledge management.

## Task Workflows

The Commander includes predefined task workflows to assist with common security and development activities. These workflows provide step-by-step guidance and AI-powered suggestions.

### Bug Bounty Hunting

A comprehensive workflow for finding security vulnerabilities in applications.

**Steps:**

1. Reconnaissance: Gather initial information about the target using commands like `security scan-domain`, `researcher search`, and `terminal nmap`.
2. Vulnerability Assessment: Identify potential security weaknesses with commands such as `security analyze-headers` and `security check-vulnerabilities`.
3. Exploitation Testing: Test identified vulnerabilities safely using commands like `security test-injection` and `coder generate`.
4. Documentation: Document findings for responsible disclosure using memory storage and file writing commands.

**AI Suggestions:**

- OpenAI GPT-4o for visual vulnerability analysis
- Anthropic Claude for detailed report crafting
- Perplexity for researching latest CVEs
- DeepSeek for code snippet analysis

### Code Security Review

Analyze code for security vulnerabilities and best practices.

**Steps:**

1. Setup: Prepare the codebase with commands like `file list`, `coder analyze-repo`, and `terminal git clone`.
2. Static Analysis: Perform static code analysis using `security static-analysis` and dependency checks.
3. Dynamic Analysis: Conduct dynamic testing with fuzz testing and scanners.
4. Report Generation: Generate comprehensive security reports and suggest fixes.

**AI Suggestions:**

- OpenAI GPT-4o for code structure analysis
- Anthropic Claude for understanding complex security patterns
- Perplexity for researching secure coding best practices
- DeepSeek for identifying subtle security issues

### Penetration Testing

Comprehensive penetration testing workflow.

**Steps:**

1. Scope Definition: Define testing scope and boundaries.
2. Information Gathering: Collect target information.
3. Vulnerability Scanning: Scan for vulnerabilities.
4. Exploitation: Attempt to exploit vulnerabilities.
5. Post-Exploitation: Gather evidence and credentials.
6. Reporting: Document findings and recommendations.

**AI Suggestions:**

- OpenAI GPT-4o for security posture analysis
- Anthropic Claude for detailed testing plans
- Perplexity for latest exploit techniques research
- DeepSeek for attack vector identification

### Secure Development Lifecycle

Implement security throughout the development lifecycle.

**Steps:**

1. Threat Modeling: Identify threats and security requirements.
2. Secure Coding: Implement secure coding practices.
3. Security Testing: Perform security-focused testing.
4. Deployment Security: Secure deployment environments.
5. Monitoring & Response: Set up monitoring and incident response.

**AI Suggestions:**

- OpenAI GPT-4o for secure code generation
- Anthropic Claude for threat modeling
- Perplexity for researching secure coding practices
- DeepSeek for early security flaw identification

## Accessing Task Workflows

You can access task workflows via the web interface at `/tasks` or through the API endpoints:

- `/task-templates`: Get available task templates
- `/task-template/<template_id>`: Get details of a specific task template
- `/task-suggestions?query=your_query`: Get task suggestions based on a query
- `/task-steps/<template_id>`: Get detailed steps for a task

## License

Specify your project's license here.
