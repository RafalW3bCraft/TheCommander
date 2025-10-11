import os
import re
import logging
import subprocess
import json
import platform
import psutil
from typing import List, Dict, Any, Optional
from agents.base_agent import BaseAgent
from ai_service import ai_service

logger = logging.getLogger(__name__)

class DevOpsAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="DevOpsAgent",
            description="Specialized in automation, deployment, and infrastructure management."
        )
        self.supported_platforms = [
            "docker", "kubernetes", "aws", "azure", "gcp", 
            "github-actions", "jenkins", "gitlab-ci", "terraform", "ansible"
        ]

    def get_commands(self):
        return {
            "docker-setup": {
                "description": "Generate Docker configuration files",
                "usage": "docker-setup <app_type> [options]",
                "examples": [
                    "docker-setup flask",
                    "docker-setup nodejs --with-database"
                ]
            },
            "ci-pipeline": {
                "description": "Create CI/CD pipeline configuration",
                "usage": "ci-pipeline <platform> <app_type>",
                "examples": [
                    "ci-pipeline github-actions python",
                    "ci-pipeline gitlab-ci nodejs"
                ]
            },
            "infrastructure": {
                "description": "Generate infrastructure as code templates",
                "usage": "infrastructure <platform> <resource_type>",
                "examples": [
                    "infrastructure terraform aws-ec2",
                    "infrastructure ansible web-server"
                ]
            },
            "monitor-setup": {
                "description": "Setup monitoring configuration",
                "usage": "monitor-setup <platform> [options]",
                "examples": [
                    "monitor-setup prometheus",
                    "monitor-setup cloudwatch --with-alarms"
                ]
            },
            "deployment": {
                "description": "Generate deployment scripts or configurations",
                "usage": "deployment <platform> <app_type>",
                "examples": [
                    "deployment kubernetes python-app",
                    "deployment heroku nodejs-app"
                ]
            }
        }

    def execute(self, command, args):
        try:
            if command == "docker-setup":
                if not args:
                    return "Error: Missing application type. Usage: docker-setup <app_type> [options]"
                app_type = args[0].lower()
                options = args[1:] if len(args) > 1 else []
                return self._docker_setup(app_type, options)

            elif command == "ci-pipeline":
                if len(args) < 2:
                    return "Error: Missing platform or application type. Usage: ci-pipeline <platform> <app_type>"
                platform = args[0].lower()
                app_type = args[1].lower()
                return self._ci_pipeline(platform, app_type)

            elif command == "infrastructure":
                if len(args) < 2:
                    return "Error: Missing platform or resource type. Usage: infrastructure <platform> <resource_type>"
                platform = args[0].lower()
                resource_type = args[1].lower()
                return self._infrastructure(platform, resource_type)

            elif command == "monitor-setup":
                if not args:
                    return "Error: Missing platform. Usage: monitor-setup <platform> [options]"
                platform = args[0].lower()
                options = args[1:] if len(args) > 1 else []
                return self._monitor_setup(platform, options)

            elif command == "deployment":
                if len(args) < 2:
                    return "Error: Missing platform or application type. Usage: deployment <platform> <app_type>"
                platform = args[0].lower()
                app_type = args[1].lower()
                return self._deployment(platform, app_type)

            else:
                return f"Unknown command: '{command}'"

        except Exception as e:
            logger.error(f"Error in DevOpsAgent: {str(e)}")
            return f"Error executing command: {str(e)}"

    def _docker_setup(self, app_type, options):
        try:
            with_database = "--with-database" in options
            multi_stage = "--multi-stage" in options

            try:
                system_prompt = f"""You are a DevOps expert specializing in Docker containerization.
Generate Docker configuration files for a {app_type} application.

Include:
1. A well-structured Dockerfile with best practices
2. Docker Compose configuration if appropriate
3. Clear comments explaining each section
4. Proper security considerations
5. Optimized image size and build process

{"Include database configuration in docker-compose.yml" if with_database else ""}
{"Use multi-stage builds for optimized images" if multi_stage else ""}

Format your response with clear file headers and code blocks."""

                response = ai_service.models['claude'].messages.create(
                    model="claude-3-5-sonnet-20241022",
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": f"Generate Docker configuration for {app_type} application"}
                    ],
                    temperature=0.2,
                    max_tokens=2000
                )
                
                return response.content[0].text
                
            except KeyError:
                return "Claude AI not available. Please configure ANTHROPIC_API_KEY to generate Docker configurations."
            except Exception as e:
                logger.error(f"Error generating Docker setup: {str(e)}")
                return f"Error generating Docker configuration: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error in _docker_setup: {str(e)}")
            return f"Error: {str(e)}"

    def _ci_pipeline(self, platform, app_type):
        try:
            try:
                system_prompt = f"""You are a DevOps expert specializing in CI/CD pipelines.
Generate a {platform} CI/CD pipeline configuration for a {app_type} application.

Include:
1. Build and test stages
2. Proper caching for dependencies
3. Linting and code quality checks
4. Security scanning
5. Deployment configuration
6. Clear comments explaining each section

Format your response with clear file headers and code blocks.
Use current best practices for {platform} and {app_type}."""

                response = ai_service.models['claude'].messages.create(
                    model="claude-3-5-sonnet-20241022",
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": f"Generate {platform} pipeline for {app_type} application"}
                    ],
                    temperature=0.2,
                    max_tokens=2000
                )
                
                return response.content[0].text
                
            except KeyError:
                return f"Claude AI not available. Please configure ANTHROPIC_API_KEY to generate {platform} pipelines."
            except Exception as e:
                logger.error(f"Error generating CI pipeline: {str(e)}")
                return f"Error generating CI/CD pipeline: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error in _ci_pipeline: {str(e)}")
            return f"Error: {str(e)}"

    def _infrastructure(self, platform, resource_type):
        try:
            try:
                system_prompt = f"""You are a DevOps expert specializing in Infrastructure as Code.
Generate {platform} configuration for {resource_type} resources.

Include:
1. Well-structured resource definitions
2. Security best practices
3. Proper variable usage
4. Clear documentation and comments
5. Scalability considerations

Format your response with clear file headers and code blocks.
Use current best practices for {platform}."""

                response = ai_service.models['claude'].messages.create(
                    model="claude-3-5-sonnet-20241022",
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": f"Generate {platform} infrastructure code for {resource_type}"}
                    ],
                    temperature=0.2,
                    max_tokens=2000
                )
                
                return response.content[0].text
                
            except KeyError:
                return f"Claude AI not available. Please configure ANTHROPIC_API_KEY to generate {platform} infrastructure."
            except Exception as e:
                logger.error(f"Error generating infrastructure: {str(e)}")
                return f"Error generating infrastructure code: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error in _infrastructure: {str(e)}")
            return f"Error: {str(e)}"

    def _monitor_setup(self, platform, options):
        try:
            with_alarms = "--with-alarms" in options
            with_dashboard = "--with-dashboard" in options

            try:
                system_prompt = f"""You are a DevOps expert specializing in monitoring and observability.
Generate {platform} monitoring configuration.

Include:
1. Metrics collection setup
2. Log aggregation configuration
3. Alert rules and thresholds
4. Dashboard definitions
5. Best practices for observability

{"Include alarm/alerting configuration" if with_alarms else ""}
{"Include dashboard configuration" if with_dashboard else ""}

Format your response with clear file headers and code blocks."""

                response = ai_service.models['claude'].messages.create(
                    model="claude-3-5-sonnet-20241022",
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": f"Generate {platform} monitoring setup"}
                    ],
                    temperature=0.2,
                    max_tokens=2000
                )
                
                return response.content[0].text
                
            except KeyError:
                return f"Claude AI not available. Please configure ANTHROPIC_API_KEY to generate {platform} monitoring."
            except Exception as e:
                logger.error(f"Error generating monitoring setup: {str(e)}")
                return f"Error generating monitoring configuration: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error in _monitor_setup: {str(e)}")
            return f"Error: {str(e)}"

    def _deployment(self, platform, app_type):
        try:
            try:
                system_prompt = f"""You are a DevOps expert specializing in application deployment.
Generate {platform} deployment configuration for a {app_type} application.

Include:
1. Deployment manifests or scripts
2. Service configuration
3. Environment variables and secrets management
4. Scaling configuration
5. Health checks and readiness probes
6. Rollback procedures

Format your response with clear file headers and code blocks.
Use current best practices for {platform} and {app_type}."""

                response = ai_service.models['claude'].messages.create(
                    model="claude-3-5-sonnet-20241022",
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": f"Generate {platform} deployment for {app_type} application"}
                    ],
                    temperature=0.2,
                    max_tokens=2000
                )
                
                return response.content[0].text
                
            except KeyError:
                return f"Claude AI not available. Please configure ANTHROPIC_API_KEY to generate {platform} deployment."
            except Exception as e:
                logger.error(f"Error generating deployment: {str(e)}")
                return f"Error generating deployment configuration: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error in _deployment: {str(e)}")
            return f"Error: {str(e)}"
