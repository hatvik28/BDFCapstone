import time
import os
import re
import subprocess
import shutil
import openai


class SolutionApplier:
    def __init__(self, google_formatter_path):
        self.google_formatter_path = google_formatter_path

    def find_and_replace_buggy_code(self, content, buggy_snippet, fixed_snippet):
        try:
            # Use ChatGPT to perform the code replacement
            prompt = f"""
            You are a Java code editor. Replace the buggy code snippet with the fixed version in the following Java code.
            If the exact buggy code snippet is not found, use the context provided and identify the code block near the original line 
            number that performs a similar function or contains similar variables/logic and replace that code bloxk with the Fixed 
            code to use!
            Only replace the exact buggy code with the fixed version. Do not modify any other parts of the code.
            Preserve all indentation, formatting, and the complete class structure including all closing braces.
            Make sure to return the ENTIRE file content, not just the changed part.

            Original Java code:
            ```java
            {content}
            ```

            Buggy code to replace:
            ```java
            {buggy_snippet}
            ```

            Fixed code to use:
            ```java
            {fixed_snippet}
            ```

            Return the complete updated Java code with the replacement made, including all class declarations, methods, and closing braces.
            """

            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a precise Java code editor that replaces specific code snippets while preserving the complete class structure and all closing braces."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent results
                max_tokens=4000  # Increased to handle larger files
            )

            corrected_code = response['choices'][0]['message']['content'].strip(
            )

            # Clean up any markdown formatting
            corrected_code = re.sub(
                r"```[a-zA-Z]*\n?", "", corrected_code).strip()

            # Verify the code has proper closing braces
            if corrected_code.count('{') != corrected_code.count('}'):
                return content  # Return original if braces don't match

            return corrected_code

        except Exception as e:
            return content

    def apply_solution(self, file_path, code_snippet, solution, solution_number=1):
        """
        Apply a solution directly to the file in cloned_repo.
        """
        try:
            # Normalize the file path and ensure it starts with cloned_repo
            if not file_path.startswith('cloned_repo'):
                file_path = os.path.join('cloned_repo', file_path)

            # Ensure target directory exists
            target_dir = os.path.dirname(file_path)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)

            # Read the current content of the file
            current_code = ""
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    current_code = f.read()
            else:
                raise FileNotFoundError(
                    f"Target file not found at {file_path}")

            # Clean the solution (remove markdown formatting)
            cleaned_solution = re.sub(r"```[a-zA-Z]*\n?", "", solution).strip()

            # Apply the fix using ChatGPT
            fixed_code = self.find_and_replace_buggy_code(
                current_code,
                code_snippet,
                cleaned_solution
            )

            if fixed_code == current_code:
                raise ValueError("No changes made — the fix was not applied.")

            # Write the fixed code back to the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)

            # Format the file (optional)
            try:
                subprocess.run(
                    ["java", "-jar", self.google_formatter_path, "-i", file_path], check=True)
            except Exception:
                pass

            return fixed_code, "Bug fixed successfully!"

        except Exception as e:
            raise

    def apply_solution_to_temp_dir(self, original_code, code_snippet, solution, filename, solution_number):
        """
        Apply a solution to a temporary directory for metrics analysis.

        Args:
            original_code: The original code content
            code_snippet: The buggy code snippet to replace
            solution: The fixed solution code to apply
            filename: The target filename
            solution_number: The solution number

        Returns:
            Path to the temporary directory containing the fixed file
        """
        # Clean the solution (remove markdown formatting)
        cleaned_solution = re.sub(r"```[a-zA-Z]*\n?", "", solution).strip()

        # Apply the fix using ChatGPT
        try:
            fixed_code = self.find_and_replace_buggy_code(
                original_code, code_snippet, cleaned_solution)

            if fixed_code == original_code:
                raise ValueError("No changes made — the fix was not applied.")

            # Create temp folder
            temp_base_dir = os.path.abspath("temp_ck")
            solution_dir = os.path.join(
                temp_base_dir, f"solution_{solution_number}")
            os.makedirs(solution_dir, exist_ok=True)

            # Write fixed file to temp directory
            temp_file_path = os.path.join(
                solution_dir, os.path.basename(filename))
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(fixed_code)

            # Format the file (optional)
            try:
                subprocess.run(
                    ["java", "-jar", self.google_formatter_path, "-i", temp_file_path], check=True)
            except Exception:
                pass

            return solution_dir  # This will be passed to CKMetricsAnalyzer

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise
