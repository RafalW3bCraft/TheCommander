import os
import re
import logging
import json
import datetime
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
from agents.base_agent import BaseAgent
from ai_service import ai_service

logger = logging.getLogger(__name__)

class LearningAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="LearningAgent",
            description="Specialized in improving agent performance through feedback and analysis."
        )
        self.usage_history = []
        self.feedback_history = []
        self.improvement_suggestions = []
        self.last_analysis_date = None
        self.load_history()

    def get_commands(self):
        return {
            "analyze-usage": {
                "description": "Analyze command usage patterns to improve recommendations",
                "usage": "analyze-usage [days]",
                "examples": [
                    "analyze-usage",
                    "analyze-usage 30"
                ]
            },
            "add-feedback": {
                "description": "Add user feedback about a command or response",
                "usage": "add-feedback <command> <rating> [comment]",
                "examples": [
                    "add-feedback 'security scan-code main.py' 5 'Very helpful output'",
                    "add-feedback 'vscode setup python' 3 'Could include more detail'"
                ]
            },
            "diagnose": {
                "description": "Run self-diagnostic to identify improvement areas",
                "usage": "diagnose [component]",
                "examples": [
                    "diagnose",
                    "diagnose security-agent"
                ]
            },
            "improvement-report": {
                "description": "Generate a report of improvement suggestions",
                "usage": "improvement-report [priority]",
                "examples": [
                    "improvement-report",
                    "improvement-report high"
                ]
            },
            "optimize-workflows": {
                "description": "Suggest workflow optimizations based on usage patterns",
                "usage": "optimize-workflows [workflow_type]",
                "examples": [
                    "optimize-workflows",
                    "optimize-workflows security"
                ]
            }
        }

    def execute(self, command, args):
        try:
            if command == "analyze-usage":
                days = 30
                if args and args[0].isdigit():
                    days = int(args[0])
                return self._analyze_usage(days)

            elif command == "add-feedback":
                if len(args) < 2:
                    return "Error: Missing required arguments. Usage: add-feedback <command> <rating> [comment]"

                cmd = args[0]
                try:
                    rating = int(args[1])
                    if rating < 1 or rating > 5:
                        return "Error: Rating must be between 1 and 5"
                except ValueError:
                    return "Error: Rating must be a number between 1 and 5"

                comment = " ".join(args[2:]) if len(args) > 2 else ""
                return self._add_feedback(cmd, rating, comment)

            elif command == "diagnose":
                component = args[0] if args else None
                return self._diagnose(component)

            elif command == "improvement-report":
                priority = args[0] if args else None
                return self._improvement_report(priority)

            elif command == "optimize-workflows":
                workflow_type = args[0] if args else None
                return self._optimize_workflows(workflow_type)

            else:
                return f"Unknown command: '{command}'"

        except Exception as e:
            logger.error(f"Error in LearningAgent: {str(e)}")
            return f"Error executing command: {str(e)}"

    def record_usage(self, command, agent, success, execution_time):
        usage_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "command": command,
            "agent": agent,
            "success": success,
            "execution_time": execution_time
        }

        self.usage_history.append(usage_entry)
        self.save_history()
        logger.debug(f"Recorded usage: {command} by {agent} (success: {success})")

    def load_history(self):
        try:
            if os.path.exists("data/usage_history.json"):
                with open("data/usage_history.json", "r") as f:
                    self.usage_history = json.load(f)
                logger.info(f"Loaded {len(self.usage_history)} usage history entries")

            if os.path.exists("data/feedback_history.json"):
                with open("data/feedback_history.json", "r") as f:
                    self.feedback_history = json.load(f)
                logger.info(f"Loaded {len(self.feedback_history)} feedback history entries")

            if os.path.exists("data/improvement_suggestions.json"):
                with open("data/improvement_suggestions.json", "r") as f:
                    self.improvement_suggestions = json.load(f)
                logger.info(f"Loaded {len(self.improvement_suggestions)} improvement suggestions")

        except Exception as e:
            logger.error(f"Error loading history: {str(e)}")

    def save_history(self):
        try:
            os.makedirs("data", exist_ok=True)

            with open("data/usage_history.json", "w") as f:
                json.dump(self.usage_history, f, indent=2)

            with open("data/feedback_history.json", "w") as f:
                json.dump(self.feedback_history, f, indent=2)

            with open("data/improvement_suggestions.json", "w") as f:
                json.dump(self.improvement_suggestions, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving history: {str(e)}")

    def _analyze_usage(self, days):
        try:
            cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()

            recent_usage = [entry for entry in self.usage_history if entry["timestamp"] >= cutoff_date]

            if not recent_usage:
                return f"No usage data found for the last {days} days."

            total_commands = len(recent_usage)
            successful_commands = sum(1 for entry in recent_usage if entry["success"])
            success_rate = (successful_commands / total_commands) * 100 if total_commands > 0 else 0

            command_counter = Counter()
            agent_counter = Counter()
            command_time = defaultdict(list)
            command_success = defaultdict(list)

            for entry in recent_usage:
                cmd = entry["command"].split()[0] if entry["command"].split() else "unknown"
                command_counter[cmd] += 1
                agent_counter[entry["agent"]] += 1
                command_time[cmd].append(entry["execution_time"])
                command_success[cmd].append(1 if entry["success"] else 0)

            popular_commands = command_counter.most_common(5)

            popular_agents = agent_counter.most_common(5)

            command_success_rates = {}
            for cmd, successes in command_success.items():
                if successes:
                    command_success_rates[cmd] = (sum(successes) / len(successes)) * 100

            command_avg_times = {}
            for cmd, times in command_time.items():
                if times:
                    command_avg_times[cmd] = sum(times) / len(times)

            result = f"Usage Analysis Report (Last {days} Days)\n\n"
            result += f"Total Commands Executed: {total_commands}\n"
            result += f"Overall Success Rate: {success_rate:.2f}%\n\n"

            result += "Most Popular Commands:\n"
            for cmd, count in popular_commands:
                success_rate = command_success_rates.get(cmd, 0)
                avg_time = command_avg_times.get(cmd, 0)
                result += f"- {cmd}: {count} uses (Success Rate: {success_rate:.2f}%, Avg Time: {avg_time:.2f}s)\n"

            result += "\nMost Used Agents:\n"
            for agent, count in popular_agents:
                result += f"- {agent}: {count} uses\n"

            result += "\nOptimization Suggestions:\n"

            low_success_commands = [cmd for cmd, rate in command_success_rates.items() if rate < 80]
            if low_success_commands:
                result += "- Commands with low success rates that may need improvement:\n"
                for cmd in low_success_commands:
                    result += f"  * {cmd} ({command_success_rates[cmd]:.2f}% success rate)\n"

            slow_commands = [cmd for cmd, time in command_avg_times.items() if time > 2.0]
            if slow_commands:
                result += "- Commands with long execution times that may need optimization:\n"
                for cmd in slow_commands:
                    result += f"  * {cmd} ({command_avg_times[cmd]:.2f}s average)\n"

            self.last_analysis_date = datetime.datetime.now().isoformat()

            try:
                if 'claude' in ai_service.models:
                    usage_data = {
                        "total_commands": total_commands,
                        "success_rate": success_rate,
                        "popular_commands": popular_commands,
                        "popular_agents": popular_agents,
                        "command_success_rates": command_success_rates,
                        "command_avg_times": command_avg_times
                    }

                    system_prompt = """You are a usage pattern analyst specializing in AI assistant systems.
Analyze the provided usage data and generate actionable insights that could improve the system.
Focus on:

1. Patterns in command usage
2. Potential bottlenecks or pain points
3. Opportunities for automation or workflow improvements
4. Command success rates and execution times
5. User preference patterns

Provide 3-5 specific, actionable recommendations based on the data."""

                    response = ai_service.models['claude'].messages.create(
                        model="claude-3-5-sonnet-20241022",
                        system=system_prompt,
                        messages=[{"role": "user", "content": json.dumps(usage_data)}],
                        temperature=0.2,
                        max_tokens=1500
                    )
                    
                    result += f"\n\nAI Insights:\n{response.content[0].text}\n"
            except Exception as e:
                logger.error(f"Error getting AI insights: {str(e)}")

            return result

        except Exception as e:
            logger.error(f"Error analyzing usage patterns: {str(e)}")
            return f"Error analyzing patterns: {str(e)}"

    def add_feedback(self, command, rating, comment=None):
        try:
            if not 1 <= rating <= 5:
                return "Error: Rating must be between 1 and 5"

            feedback = {
                "timestamp": datetime.datetime.now().isoformat(),
                "command": command,
                "rating": rating,
                "comment": comment
            }

            self.user_feedback.append(feedback)
            self.save_history()

            return f"Feedback recorded for command: {command}"

        except Exception as e:
            logger.error(f"Error adding feedback: {str(e)}")
            return f"Error recording feedback: {str(e)}"

    def run_diagnostic(self, component=None):
        try:
            result = "System Diagnostic Report\n"
            result += "=" * 50 + "\n\n"

            command_stats = {}
            for entry in self.command_history:
                cmd = entry.get('command', 'unknown')
                if cmd not in command_stats:
                    command_stats[cmd] = {'total': 0, 'success': 0, 'total_time': 0}
                command_stats[cmd]['total'] += 1
                if entry.get('success', False):
                    command_stats[cmd]['success'] += 1
                command_stats[cmd]['total_time'] += entry.get('execution_time', 0)

            result += "Command Performance:\n"
            for cmd, stats in command_stats.items():
                success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
                avg_time = stats['total_time'] / stats['total'] if stats['total'] > 0 else 0
                result += f"- {cmd}: {success_rate:.1f}% success, {avg_time:.2f}s avg\n"

            return result

        except Exception as e:
            logger.error(f"Error running diagnostic: {str(e)}")
            return f"Error running diagnostic: {str(e)}"

    def get_improvement_suggestions(self, priority=None):
        try:
            suggestions = self.improvement_suggestions
            if priority:
                suggestions = [s for s in suggestions if s.get('priority') == priority.lower()]

            if not suggestions:
                return f"No improvement suggestions found{' for priority: ' + priority if priority else ''}."

            result = "Improvement Suggestions\n"
            result += "=" * 50 + "\n\n"

            for suggestion in suggestions:
                result += f"Priority: {suggestion.get('priority', 'medium').upper()}\n"
                result += f"Source: {suggestion.get('source', 'unknown')}\n"
                result += f"Suggestion: {suggestion.get('suggestion', '')}\n"
                result += f"Status: {suggestion.get('status', 'open')}\n"
                result += "-" * 50 + "\n"

            return result

        except Exception as e:
            logger.error(f"Error getting improvement suggestions: {str(e)}")
            return f"Error: {str(e)}"

    def suggest_workflow_optimization(self, workflow_type=None):
        try:
            result = "Workflow Optimization Suggestions\n"
            result += "=" * 50 + "\n\n"

            sessions = {}
            for entry in self.command_history:
                session_id = entry.get('session_id', 'default')
                if session_id not in sessions:
                    sessions[session_id] = []
                sessions[session_id].append(entry.get('command', 'unknown'))

            result += "Based on your usage patterns:\n\n"
            result += "- Consider creating shortcuts for frequently used command sequences\n"
            result += "- Group related operations into workflows\n"
            result += "- Set up templates for recurring tasks\n"

            return result

        except Exception as e:
            logger.error(f"Error suggesting workflow optimization: {str(e)}")
            return f"Error: {str(e)}"

    def find_common_subsequences(self, sequences, min_length=2, min_count=2):
        subsequence_counts = defaultdict(int)

        for sequence in sequences:
            for i in range(len(sequence) - min_length + 1):
                for j in range(i + min_length, len(sequence) + 1):
                    subseq = tuple(sequence[i:j])
                    subsequence_counts[subseq] += 1

        common_subseqs = {seq: count for seq, count in subsequence_counts.items() if count >= min_count}

        return common_subseqs

    def add_improvement_suggestion(self, suggestion, source, priority="medium", feedback=None):
        try:
            improvement = {
                "timestamp": datetime.datetime.now().isoformat(),
                "source": source,
                "suggestion": suggestion,
                "status": "open",
                "priority": priority.lower()
            }

            if feedback:
                improvement["feedback"] = feedback

            self.improvement_suggestions.append(improvement)
            self.save_history()

            return True

        except Exception as e:
            logger.error(f"Error adding improvement suggestion: {str(e)}")
            return False
