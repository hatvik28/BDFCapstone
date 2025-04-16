import openai
import re


class LLMModel:
    def __init__(self, api_key):
        openai.api_key = api_key

    def generate_solution(self, bug_type, description, line, code_snippet, file_content):
        """Generates solutions for a bug using both the bug snippet and the full Java file."""

        guideline = [
            {"role": "system", "content": "You are a Java bug-fixing assistant that generates accurate and complete solutions. Always consider variable reuse and proper scope when fixing bugs."},
            {
                "role": "user",
                "content": f"""
                The following Java file contains a bug:
                
                --- FULL JAVA FILE START ---
                {file_content}
                --- FULL JAVA FILE END ---

                The bug is located in the following part of the code:
                - **Bug Type**: {bug_type}
                - **Description**: {description}
                - **Line**: {line}
                - **Code Snippet**:
                {code_snippet}

                Provide 3 solutions to fix this bug. Each solution must contain:
                1. A corrected code snippet that shows ONLY the fixed part of the code.
                2. When handling method return values that could be null (like file paths, optional values, or collection lookups), always:
                    - Assign the return value to a local variable.
                    - Check that variable for null.
                    - Then use the variable.
                    This is important to satisfy tools like SpotBugs and prevent false positives for null dereferences.

                3. For other potential exceptions or error conditions, include proper error handling and validation appropriate to the specific bug type.
                4. Include ALL necessary lines of code for the solution to work properly, not just the changed line.
                5. An explanation of the fix that includes both what was changed and why.
                6. A rating out of 10. The highest-rated solution should be displayed FIRST.
            
    
                Format your response as follows:
                Solution X (Rating X/10):
                ```java
                // Complete code snippet with full context
                ```
                Explanation: <detailed explanation of the fix and why it works>
                
                """
            }
        ]

        payload = {
            "model": "gpt-4o",
            "messages": guideline,
            "temperature": 0.2,
            "top_p": 0.9,
            "max_tokens": 1500
        }

        try:
            response = openai.ChatCompletion.create(**payload)
            return response['choices'][0]['message']['content']
        except Exception as e:
            raise Exception(f"Error generating solutions: {str(e)}")

    def parse_solutions(self, response_text):
        """Parses the LLM's response into structured solution data."""
        solutions = []
        current_solution = {"solution": "", "explanation": "", "rating": 0}
        lines = response_text.splitlines()

        for line in lines:
            match = re.match(r"Solution (\d+) \(Rating (\d+)/10\):", line)
            if match:
                if current_solution["solution"]:
                    solutions.append(current_solution)

                current_solution = {
                    "solution": "",
                    "explanation": "",
                    "rating": int(match.group(2))
                }

            elif line.startswith("Explanation:"):
                current_solution["explanation"] = line.replace(
                    "Explanation:", "").strip()

            elif current_solution.get("solution") is not None:
                current_solution["solution"] += line + "\n"

        # Append the last solution if present
        if current_solution["solution"]:
            solutions.append(current_solution)

        return solutions

    def update_solution(self, bug_type, description, original_code, current_solution, user_feedback):
        """Update a solution based on user feedback."""
        if not user_feedback:
            raise ValueError("User feedback is required")

        prompt = f"""You are a Java bug fixing assistant. You previously generated a solution for a bug, but the user has provided feedback that it needs improvement.

                Bug Type: {bug_type}
                Bug Description: {description}

                Original File Content:
                ```java
                {original_code}
                ```

                Previous Solution Snippet:
                ```java
                {current_solution}
                ```

                User Feedback:
                {user_feedback}

                YOU MUST FORMAT YOUR RESPONSE EXACTLY AS SHOWN BELOW:

                FULL_FILE:
                ```java
                // This must be the complete Java file with the fix applied
                // Copy the entire original file content and apply your changes to it
                // Include all class declarations, imports, and package statements
                {original_code}  // Start with this and modify it
                ```

                SNIPPET:
                ```java
                // This must be only the modified part that replaces the buggy code
                // Do not include the entire file here, just the specific fix
                <paste only the changed code here>
                ```

                IMPORTANT: 
                1. The FULL_FILE section must contain the complete Java file with your fix applied
                2. The SNIPPET section must contain only the modified code that replaces the buggy part
                3. Do not include any other text or explanations
                4. Make sure the FULL_FILE section preserves the entire class structure"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a precise Java code editor that maintains complete file structure while applying fixes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1  # Lower temperature for more consistent formatting
            )

            response_text = response.choices[0]['message']['content'].strip()

            # Try multiple parsing patterns
            patterns = [
                # Standard format
                (r"FULL_FILE:\s*```java\s*(.*?)\s*```.*?SNIPPET:\s*```java\s*(.*?)\s*```", re.DOTALL),
                # Without java specification
                (r"FULL_FILE:\s*```\s*(.*?)\s*```.*?SNIPPET:\s*```\s*(.*?)\s*```", re.DOTALL),
                # Just code blocks
                (r"```java\s*(.*?)\s*```.*?```java\s*(.*?)\s*```", re.DOTALL),
                (r"```\s*(.*?)\s*```.*?```\s*(.*?)\s*```", re.DOTALL)
            ]

            full_file = None
            snippet = None

            # Try each pattern until we find a match
            for pattern, flags in patterns:
                match = re.search(pattern, response_text, flags)
                if match:
                    full_file = match.group(1).strip()
                    snippet = match.group(2).strip()
                    break

            # If no patterns matched, try to extract any code blocks
            if not full_file or not snippet:
                code_blocks = re.findall(
                    r"```(?:java)?\s*(.*?)\s*```", response_text, re.DOTALL)
                if len(code_blocks) >= 2:
                    full_file = code_blocks[0].strip()
                    snippet = code_blocks[1].strip()
                elif len(code_blocks) == 1:
                    full_file = code_blocks[0].strip()
                    snippet = code_blocks[0].strip()

            # Final validation
            if not full_file or not snippet:
                raise Exception("Could not extract code from LLM response")

            return {
                "full_file": full_file,
                "snippet": snippet
            }

        except Exception as e:
            raise Exception(f"Failed to update solution: {str(e)}")

