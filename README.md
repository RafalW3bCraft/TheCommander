# The Commander - AI Agent

This project is a Flask-based AI agent system called "The Commander" that integrates with advanced AI models such as Anthropic Claude and OpenAI to provide natural language understanding, command execution, workflow automation, and more.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd VS-Linux-AI-Agent

```

2. (Optional) Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install required Python packages:

```bash
pip install -r requirements.txt
```

> Note: If `requirements.txt` is not present, please install dependencies manually as needed.

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
- The app provides various API endpoints for command execution, workflows, image analysis, code review, and more.

## Notes

- Make sure to set the required API keys before running the app to enable AI features.
- The app uses Flask's built-in development server and is intended for development and testing purposes. For production deployment, consider using a production-ready WSGI server.

## License

Specify your project's license here.
