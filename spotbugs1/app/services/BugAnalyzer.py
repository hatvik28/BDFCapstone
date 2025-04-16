import os
import subprocess
import xml.etree.ElementTree as ET
import openai
import re
import glob
from typing import List, Tuple
import shutil


class BugAnalyzer:
    def __init__(self, output_dir: str, bin_dir: str, spotbugs_path: str, repo_root_dir: str):
        """Initialize the BugAnalyzer with necessary paths."""
        # Convert all paths to absolute paths
        self.output_dir = os.path.abspath(output_dir)
        self.bin_dir = os.path.abspath(bin_dir)
        self.spotbugs_path = os.path.abspath(spotbugs_path)
        self.repo_root_dir = os.path.abspath(repo_root_dir)

    def run_spotbugs_analysis(self, report_path):
        if os.path.exists(report_path):
            os.remove(report_path)

        # Check if there are any .class files to analyze
        class_files = []
        for root, _, files in os.walk(self.bin_dir):
            for file in files:
                if file.endswith(".class"):
                    class_files.append(os.path.join(root, file))

        if not class_files:
            raise RuntimeError(
                f"No compiled .class files found in {self.bin_dir}")

        spotbugs_command = [
            self.spotbugs_path,
            "-textui",
            "-effort:max",  # Maximum precision analysis
            "-low",      # Only report medium and high priority bugs
            "-xml",        # XML output
            "-output", report_path,
            # Omit visitors that often give false positives
            "-omitVisitors", "FindDeadLocalStores,FindUnrelatedTypesInGenericContainer",
            # Only analyze specific bug categories
            "-bugCategories", "BAD_PRACTICE,CORRECTNESS,PERFORMANCE,SECURITY",
            self.bin_dir
        ]

        try:
            subprocess.run(spotbugs_command, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"SpotBugs analysis failed: {e}")

    def parse_spotbugs_xml(self, report_path, bug_descriptions):
        """Parse the SpotBugs XML report and return a list of bugs."""

        if not os.path.exists(report_path) or os.stat(report_path).st_size == 0:
            return []

        issues = []
        unique_bugs = set()

        tree = ET.parse(report_path)
        root = tree.getroot()

        for bug_instance in root.findall('BugInstance'):
            category = bug_instance.get('category')
            severity = bug_instance.get('priority')
            bug_type = bug_instance.get('type')
            base_description = bug_descriptions.get(
                bug_type, "No description available.")

            file_path = None
            assign_line = None
            propagation_line = None
            deref_line = None

            # Process all SourceLine elements
            for source_line in bug_instance.findall('SourceLine'):
                file_path = source_line.get('sourcepath')
                line_number = source_line.get('start')
                role = source_line.get('role')

                if bug_type.startswith("NP_"):
                    # Null bugs → collect trace lines
                    if role == 'SOURCE_LINE_NULL_VALUE':
                        assign_line = line_number
                    elif role == 'SOURCE_LINE_KNOWN_NULL':
                        propagation_line = line_number
                    elif role == 'SOURCE_LINE_INVOKED':
                        deref_line = line_number
                else:
                    # For other bugs (STYLE, I18N, etc) → report first line found
                    if deref_line is None:
                        deref_line = line_number

            # If dereference line not found for NP bugs, fallback
            if not deref_line:
                deref_line = assign_line or propagation_line or line_number

            # Normalize file path
            if file_path:
                file_path = file_path.strip('/')
                file_path = file_path.replace('/', os.sep)

                possible_paths = [
                    file_path,
                    os.path.join('src', 'main', 'java', file_path),
                    os.path.basename(file_path)
                ]

                for path in possible_paths:
                    if os.path.exists(os.path.join(self.output_dir, path)):
                        file_path = path
                        break
                else:
                    file_path = "Unknown file"
            else:
                file_path = "Unknown file"

            # Generate description
            if bug_type.startswith("NP_"):
                context_description = f"{base_description}\n\nRoot Cause Trace:"
                if assign_line:
                    context_description += f"\n- Line {assign_line}: Variable may be assigned null."
                if propagation_line:
                    context_description += f"\n- Line {propagation_line}: Variable passed without null check."
                if deref_line:
                    context_description += f"\n- Line {deref_line}: Variable dereferenced without null check. (Bug here)"
            else:
                context_description = base_description

            bug_key = (file_path, deref_line, category,
                       severity, bug_type, context_description)

            if bug_key not in unique_bugs:
                unique_bugs.add(bug_key)
                issues.append({
                    "file": file_path,
                    "line": deref_line,
                    "category": category,
                    "severity": severity,
                    "type": bug_type,
                    "description": context_description
                })

        return issues

    def extract_code_snippet(self, file_path, line_number, bug_description):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            # Convert line_number to integer
            try:
                line_number = int(line_number)
            except ValueError:
                line_number = 1

            # Adjust for zero-indexing
            line_idx = line_number - 1

            # Get the exact line where the bug occurs
            if 0 <= line_idx < len(lines):
                exact_line = lines[line_idx].strip()
            else:
                exact_line = "ERROR: Line number out of range"

            # Create a window: 2 lines before + bug line + 2 after
            start = max(0, line_number - 3)
            end = min(len(lines), line_number + 2)
            context_code = "".join(lines[start:end]).strip()

            # Construct GPT prompt
            prompt = f"""
            You are an expert Java code analyzer. You must follow these instructions PRECISELY.

            Here is a snippet from a Java file with line numbers:
            ```
            {context_code}
            ```

            The bug is on line number {line_number}. The exact text on that line is:
            ```
            {exact_line}
            ```
            
            Description of the bug: "{bug_description}"

            YOUR TASK:
            1. Extract the COMPLETE statement where the bug occurs.
            2. NEVER modify the code - not even a single character.
            3. DO NOT add any null checks or suggest fixes.
            4. If the statement spans multiple lines, include all lines of the statement.
            5. If the statement is part of a control structure (if, while, for, etc.), include the entire statement including its body ONLY if necessary to understand the bug.
            
            Return ONLY the exact code from the file. No explanations. No formatting changes. No placeholders.
                """

            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "You are a Java code analyzer that extracts exact code without modifications."},
                          {"role": "user", "content": prompt}],
                temperature=0.1,  # Lower temperature for more deterministic output
                max_tokens=400
            )

            extracted_snippet = response['choices'][0]['message']['content'].strip(
            )

            # Remove Markdown code block markers (e.g., ```java or ```)
            cleaned_snippet = re.sub(
                r"```[a-zA-Z]*\n?", "", extracted_snippet).strip()

            return cleaned_snippet

        except Exception as e:
            return f"Error extracting snippet using ChatGPT: {str(e)}"
