import os
import re
import subprocess
import logging
import tempfile
from agents.base_agent import BaseAgent
from ai_service import ai_service

logger = logging.getLogger(__name__)

class CoderAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(
            name="CoderAgent",
            description="Specialized in code generation, debugging, and explaining code."
        )
        self.supported_languages = [
            "python", "javascript", "html", "css", "bash", 
            "json", "markdown", "sql"
        ]
    
    def get_commands(self):
        return {
            "write": {
                "description": "Generate code in a specified language",
                "usage": "write <language> <description>",
                "examples": [
                    "write python 'A function to sort a list of numbers'",
                    "write javascript 'A function to validate email addresses'"
                ]
            },
            "explain": {
                "description": "Explain a block of code",
                "usage": "explain <language> <code>",
                "examples": [
                    "explain python 'def factorial(n): return 1 if n <= 1 else n * factorial(n-1)'"
                ]
            },
            "debug": {
                "description": "Identify and fix issues in code",
                "usage": "debug <language> <buggy_code>",
                "examples": [
                    "debug python 'def divide(a, b): return a/b'"
                ]
            },
            "run": {
                "description": "Execute a code snippet (currently supports Python only)",
                "usage": "run <language> <code>",
                "examples": [
                    "run python 'print(\"Hello, world!\")'"
                ]
            },
            "languages": {
                "description": "List supported programming languages",
                "usage": "languages",
                "examples": ["languages"]
            }
        }
    
    def execute(self, command, args):
        try:
            if command == "languages":
                return self._list_languages()
            
            if not args:
                return f"Error: Missing arguments for '{command}' command. Use 'help coder' for usage information."
            
            if command == "write":
                if len(args) < 2:
                    return "Error: Missing language or description. Usage: write <language> <description>"
                lang = args[0].lower()
                description = " ".join(args[1:])
                return self._write_code(lang, description)
                
            elif command == "explain":
                if len(args) < 2:
                    return "Error: Missing language or code. Usage: explain <language> <code>"
                lang = args[0].lower()
                code = " ".join(args[1:])
                return self._explain_code(lang, code)
                
            elif command == "debug":
                if len(args) < 2:
                    return "Error: Missing language or code. Usage: debug <language> <code>"
                lang = args[0].lower()
                code = " ".join(args[1:])
                return self._debug_code(lang, code)
                
            elif command == "run":
                if len(args) < 2:
                    return "Error: Missing language or code. Usage: run <language> <code>"
                lang = args[0].lower()
                code = " ".join(args[1:])
                return self._run_code(lang, code)
                
            else:
                return f"Unknown command: '{command}'"
                
        except Exception as e:
            logger.error(f"Error in CoderAgent: {str(e)}")
            return f"Error executing command: {str(e)}"
    
    def _list_languages(self):
        result = "Supported programming languages:\n"
        for lang in self.supported_languages:
            result += f"- {lang}\n"
        return result
    
    def _write_code(self, language, description):
        if language not in self.supported_languages:
            return f"Sorry, {language} is not supported. Use 'languages' to see supported languages."
        
        try:
            try:
                logger.debug(f"Using AI Service to generate {language} code for: {description}")
                ai_generated = ai_service.generate_code(language, description)
                
                if ai_generated and "Error" not in ai_generated:
                    if "```" not in ai_generated:
                        result = f"Generated {language} code for: {description}\n\n```{language}\n{ai_generated}\n```"
                    else:
                        result = f"Generated {language} code for: {description}\n\n{ai_generated}"
                    return result
            except Exception as ai_err:
                logger.warning(f"AI Service code generation failed: {str(ai_err)}. Falling back to pattern-based generation.")
            
            if language == "python":
                if "sort" in description.lower():
                    code = "def sort_numbers(numbers):\n    \"\"\"Sort a list of numbers in ascending order.\"\"\"\n    return sorted(numbers)\n\n# Example usage\nnumbers = [5, 2, 8, 1, 9]\nsorted_numbers = sort_numbers(numbers)\nprint(sorted_numbers)  # Output: [1, 2, 5, 8, 9]"
                elif "factorial" in description.lower():
                    code = "def factorial(n):\n    \"\"\"Calculate the factorial of a number.\"\"\"\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n\n# Example usage\nresult = factorial(5)\nprint(result)  # Output: 120"
                elif "fibonacci" in description.lower():
                    code = "def fibonacci(n):\n    \"\"\"Generate the Fibonacci sequence up to n terms.\"\"\"\n    sequence = []\n    a, b = 0, 1\n    for _ in range(n):\n        sequence.append(a)\n        a, b = b, a + b\n    return sequence\n\n# Example usage\nfib_sequence = fibonacci(10)\nprint(fib_sequence)  # Output: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]"
                else:
                    code = f"# Code to {description}\n\ndef main():\n    # Your implementation here\n    pass\n\nif __name__ == \"__main__\":\n    main()"
            
            elif language == "javascript":
                if "sort" in description.lower():
                    code = "/**\n * Sort an array of numbers in ascending order.\n * @param {number[]} numbers - The array to sort\n * @return {number[]} The sorted array\n */\nfunction sortNumbers(numbers) {\n    return numbers.slice().sort((a, b) => a - b);\n}\n\n// Example usage\nconst numbers = [5, 2, 8, 1, 9];\nconst sortedNumbers = sortNumbers(numbers);\nconsole.log(sortedNumbers);  // Output: [1, 2, 5, 8, 9]"
                elif "email" in description.lower() and "valid" in description.lower():
                    code = "/**\n * Validate an email address.\n * @param {string} email - The email to validate\n * @return {boolean} True if valid, false otherwise\n */\nfunction validateEmail(email) {\n    const regex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;\n    return regex.test(email);\n}\n\n// Example usage\nconsole.log(validateEmail('test@example.com'));  // Output: true\nconsole.log(validateEmail('invalid-email'));     // Output: false"
                else:
                    code = f"/**\n * {description}\n */\nfunction main() {{\n    // Your implementation here\n}}\n\n// Example usage\nmain();"
            
            elif language == "html":
                code = "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Document</title>\n    <style>\n        /* CSS styles here */\n        body {\n            font-family: Arial, sans-serif;\n            line-height: 1.6;\n            margin: 0;\n            padding: 20px;\n        }\n    </style>\n</head>\n<body>\n    <h1>Hello World</h1>\n    <p>This is a basic HTML template.</p>\n    \n    <script>\n        // JavaScript code here\n        console.log('Page loaded');\n    </script>\n</body>\n</html>"
            
            else:
                code = f"// Generated code for {description} in {language}\n// This is a placeholder. Implement actual code generation for {language}."
            
            result = f"Generated {language} code for: {description}\n\n```{language}\n{code}\n```"
            return result
        
        except Exception as e:
            logger.error(f"Error generating code: {str(e)}")
            return f"Error generating code: {str(e)}"
    
    def _explain_code(self, language, code):
        if language not in self.supported_languages:
            return f"Sorry, {language} is not supported. Use 'languages' to see supported languages."
        
        try:
            code = re.sub(r'^```.*\n|```$', '', code.strip())
            
            try:
                logger.debug(f"Using AI Service to explain {language} code")
                ai_explanation = ai_service.explain_code(language, code)
                
                if ai_explanation and "Error" not in ai_explanation:
                    result = f"Code explanation ({language}):\n\n```{language}\n{code}\n```\n\nExplanation:\n{ai_explanation}"
                    return result
            except Exception as ai_err:
                logger.warning(f"AI Service code explanation failed: {str(ai_err)}. Falling back to pattern-based explanation.")
            
            if language == "python":
                if "def factorial" in code:
                    explanation = "This code defines a recursive factorial function. It calculates the factorial of a number 'n', which is the product of all positive integers less than or equal to n.\n\n- Base case: If n is 0 or 1, it returns 1\n- Recursive case: For n > 1, it returns n multiplied by factorial(n-1)\n\nFactorial is commonly used in combinatorics and probability theory."
                elif "def fibonacci" in code:
                    explanation = "This code generates a Fibonacci sequence up to n terms. In a Fibonacci sequence, each number is the sum of the two preceding ones, starting from 0 and 1.\n\nThe algorithm:\n- Initializes variables a=0 and b=1\n- For each iteration, adds 'a' to the sequence\n- Updates a and b using parallel assignment: a becomes b, and b becomes a+b"
                else:
                    explanation = f"This is a {language} code snippet. It appears to " + (
                        "define a function. Functions in Python are created using the 'def' keyword and can accept parameters."
                        if "def" in code else
                        "contain some Python code. Python is an interpreted, high-level, general-purpose programming language."
                    )
            
            elif language == "javascript":
                if "function" in code:
                    explanation = f"This is a JavaScript function. In JavaScript, functions are first-class objects that can be passed around and used as variables."
                elif "const" in code or "let" in code or "var" in code:
                    explanation = "This JavaScript code declares variables. Modern JavaScript uses 'const' for values that won't change, 'let' for values that might change, and 'var' (older style) for function-scoped variables."
                else:
                    explanation = "This is a JavaScript code snippet. JavaScript is a high-level, interpreted programming language that's commonly used for web development."
            
            else:
                explanation = f"This appears to be {language} code. I can provide basic explanations for this language, but my capabilities are limited to simple pattern recognition."
            
            result = f"Code explanation ({language}):\n\n```{language}\n{code}\n```\n\nExplanation:\n{explanation}"
            return result
        
        except Exception as e:
            logger.error(f"Error explaining code: {str(e)}")
            return f"Error explaining code: {str(e)}"
    
    def _debug_code(self, language, code):
        if language not in self.supported_languages:
            return f"Sorry, {language} is not supported. Use 'languages' to see supported languages."
        
        try:
            code = re.sub(r'^```.*\n|```$', '', code.strip())
            
            try:
                logger.debug(f"Using AI Service to debug {language} code")
                ai_analysis = ai_service.analyze_code(language, code, analysis_type="debug")
                
                if ai_analysis and "Error" not in ai_analysis:
                    result = f"Debug Analysis ({language}):\n\n"
                    result += f"Original code:\n```{language}\n{code}\n```\n\n"
                    result += f"Analysis and Fixes:\n{ai_analysis}"
                    return result
            except Exception as ai_err:
                logger.warning(f"AI Service code debugging failed: {str(ai_err)}. Falling back to pattern-based debugging.")
            
            if language == "python":
                issues = []
                fixed_code = code
                
                if "def divide" in code and "/" in code and not "if" in code:
                    issues.append("Potential division by zero error: The function doesn't check if the divisor is zero.")
                    fixed_code = re.sub(
                        r'def\s+divide\s*\(([^)]*)\)\s*:\s*\n?\s*return\s+([^/]+)/([^;\n]+)',
                        r'def divide(\1):\n    if \3 == 0:\n        raise ValueError("Cannot divide by zero")\n    return \2/\3',
                        code
                    )
                
                elif "def" in code and not "return" in code:
                    issues.append("Function doesn't return a value: Add a return statement.")
                    fixed_code = code.rstrip() + "\n    return None\n"
                
                elif "for" in code and ":" in code and not "in" in code:
                    issues.append("Incomplete for loop: Missing 'in' keyword and iterable.")
                    fixed_code = re.sub(
                        r'for\s+([^:]+):',
                        r'for \1 in range(10):',
                        code
                    )
                
                else:
                    issues.append("No obvious issues detected, but I recommend testing the code with various inputs.")
                
                result = "Debug Analysis:\n\n"
                result += "Original code:\n```python\n" + code + "\n```\n\n"
                result += "Issues found:\n"
                for i, issue in enumerate(issues, 1):
                    result += f"{i}. {issue}\n"
                
                if fixed_code != code:
                    result += "\nFixed code:\n```python\n" + fixed_code + "\n```"
                else:
                    result += "\nNo automatic fixes applied."
                
                return result
            
            elif language == "javascript":
                issues = []
                fixed_code = code
                
                if "=" in code and "==" not in code and "===" not in code and "if" in code:
                    issues.append("Possible assignment instead of comparison: Using '=' instead of '==' or '===' in a condition.")
                    fixed_code = re.sub(
                        r'if\s*\(([^=)]+)=([^=)])\)',
                        r'if (\1===\2)',
                        code
                    )
                
                elif "function" in code and not ";" in code:
                    issues.append("Missing semicolons: JavaScript statements traditionally end with semicolons.")
                
                else:
                    issues.append("No obvious issues detected, but I recommend testing the code with various inputs.")
                
                result = "Debug Analysis:\n\n"
                result += "Original code:\n```javascript\n" + code + "\n```\n\n"
                result += "Issues found:\n"
                for i, issue in enumerate(issues, 1):
                    result += f"{i}. {issue}\n"
                
                if fixed_code != code:
                    result += "\nFixed code:\n```javascript\n" + fixed_code + "\n```"
                else:
                    result += "\nNo automatic fixes applied."
                
                return result
            
            else:
                return f"Debugging for {language} is limited. Here's some general advice: check for syntax errors, ensure proper variable definitions, and test with different inputs."
        
        except Exception as e:
            logger.error(f"Error debugging code: {str(e)}")
            return f"Error debugging code: {str(e)}"
    
    def _run_code(self, language, code):
        if language.lower() != "python":
            return f"Sorry, code execution is currently only supported for Python. {language} execution is not available."
        
        try:
            code = re.sub(r'^```.*\n|```$', '', code.strip())
            
            with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as tmp:
                tmp_path = tmp.name
                tmp.write(code)
            
            result = subprocess.run(
                ["python", tmp_path], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {tmp_path}: {e}")
            
            if result.returncode == 0:
                output = result.stdout
                if not output:
                    output = "(No output)"
                return f"Output:\n```\n{output}\n```"
            else:
                return f"Error:\n```\n{result.stderr}\n```"
            
        except subprocess.TimeoutExpired:
            try:
                if 'tmp_path' in locals():
                    os.unlink(tmp_path)
            except:
                pass
            return "Error: Code execution timed out (10 seconds limit)."
            
        except Exception as e:
            logger.error(f"Error running code: {str(e)}")
            try:
                if 'tmp_path' in locals():
                    os.unlink(tmp_path)
            except:
                pass
            return f"Error running code: {str(e)}"
