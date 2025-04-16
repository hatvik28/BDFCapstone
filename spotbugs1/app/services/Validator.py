import os
import glob
import subprocess
from app.services.BugAnalyzer import BugAnalyzer
from app.services.PMDAnalyzer import PMDAnalyzer
from app.services.BuildSystemManager import BuildSystemManager


class Validator:
    """
    Validates a bug fix by performing bug analysis:
    1. Bug-specific validation - checks if the specific bug was fixed
    2. Other bugs validation - checks for other remaining bugs
    """

    def __init__(self, output_dir, bin_dir, spotbugs_path, bug_analyzer: BugAnalyzer, pmd_analyzer: PMDAnalyzer = None, build_system_manager: BuildSystemManager = None):
        self.output_dir = output_dir
        self.bin_dir = bin_dir
        self.spotbugs_path = spotbugs_path
        self.bug_analyzer = bug_analyzer
        self.pmd_analyzer = pmd_analyzer
        self.build_system_manager = build_system_manager

    def validate_bug(self, filename: str, bug_line: str, bug_type: str, bug_descriptions, original_code: str, patched_code: str, tool: str = 'spotbugs') -> dict:
        """
        Performs bug fix validation using static analysis.
        Returns a dictionary with validation results including:
        - bug_fixed: whether the specific bug was fixed
        - other_bugs: list of other bugs still present
        """
        try:
            # Initialize results
            results = {
                'bug_fixed': False,
                'other_bugs': []
            }

            # Check for common formatting issues in the patched code
            if patched_code and len(patched_code) > 100:
                # Check if the patched code seems to have line numbers prepended
                if patched_code.strip().startswith("123456789") and "package" in patched_code:
                    # Find the first actual code line (usually starts with 'package' or 'import')
                    for keyword in ["package", "import", "public", "class"]:
                        if keyword in patched_code:
                            code_start = patched_code.find(keyword)
                            if code_start > 0:
                                patched_code = patched_code[code_start:]
                                break

            # Perform bug-specific validation
            if tool.lower() == 'pmd':

                validation_result = self._validate_pmd_bug(
                    filename, bug_line, bug_type, original_code, patched_code)
            else:
                validation_result = self._validate_spotbugs_bug(
                    filename, bug_line, bug_type, bug_descriptions, original_code, patched_code)

            results['bug_fixed'] = validation_result['bug_fixed']
            results['other_bugs'] = validation_result['other_bugs']

            return results

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'bug_fixed': False,
                'other_bugs': [],
                'error': str(e)
            }

    def _validate_spotbugs_bug(self, filename: str, bug_line: str, bug_type: str, bug_descriptions, original_code: str, patched_code: str) -> dict:
        """Validate a bug using SpotBugs analysis, considering file, type, and line range."""
        file_path = os.path.join(self.output_dir, filename)
        report_path = os.path.join(self.output_dir, "spotbugs_report.xml")

        try:
            # Ensure compilation happens before analysis
            self.build_system_manager.compile_java_files(
                file_path, self.bin_dir)
            self.bug_analyzer.run_spotbugs_analysis(report_path)

            # Get all bugs from the report
            all_bugs_in_report = self.bug_analyzer.parse_spotbugs_xml(
                report_path, bug_descriptions)

            # 1. Filter bugs to only include those from the target file
            normalized_target_filename = self._normalize_filename(filename)
            file_bugs = [bug for bug in all_bugs_in_report
                         if self._normalize_filename(bug.get('file', '')) == normalized_target_filename]

            # Convert bug_line to integer for comparison
            try:
                bug_line_int = int(bug_line.strip())
            except ValueError:
                bug_line_int = -1

            # Define a range around the original bug line to account for line shifts
            line_range = 5  # Look 5 lines before and after the original line
            min_line = max(1, bug_line_int - line_range)
            max_line = bug_line_int + line_range

            # 2. Find specific bug by type within the file_bugs and line range
            specific_bug_exists = False
            # Iterate only over bugs from the target file
            for bug in file_bugs:
                # Check if the bug type matches (case insensitive)
                if bug.get('type', '').lower() == bug_type.lower():
                    try:
                        bug_line_in_report = int(bug.get('line', '-1').strip())
                        # Check if line is within range
                        if min_line <= bug_line_in_report <= max_line:
                            specific_bug_exists = True
                            # Found the specific bug instance (or one like it nearby)
                            break
                    except ValueError:
                        continue  # Skip if line number isn't valid

            # Prepare results based on whether the specific bug was found in the correct file/range
            if not specific_bug_exists:
                # Return 'other_bugs' only from the current file
                return {
                    'bug_fixed': True,
                    'other_bugs': file_bugs  # Return all bugs found in this file
                }
            else:
                # 3. Get other bugs (only from the *current file*, excluding the specific bug type)
                # Filter from file_bugs, not all_bugs_in_report
                other_bugs = [bug for bug in file_bugs if bug.get(
                    'type', '').lower() != bug_type.lower()]
            return {
                'bug_fixed': False,  # False because we found the specific bug
                'other_bugs': other_bugs  # Return other bugs only from this file
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'bug_fixed': False,
                'other_bugs': []
            }

    # Helper method to normalize filenames for comparison
    def _normalize_filename(self, filename: str) -> str:
        """Normalize filename to handle different path formats."""
        if not filename:
            return ""
        # Remove path and convert to lowercase for case-insensitive comparison
        return os.path.basename(filename).lower().strip()

    def _validate_pmd_bug(self, filename: str, bug_line: str, bug_type: str, original_code: str, patched_code: str) -> dict:
        """Validate a bug using PMD analysis."""
        file_path = os.path.join(self.output_dir, filename)
        report_path = os.path.join(self.output_dir, "pmd_report.xml")

        try:
            self.pmd_analyzer.run_pmd_analysis(file_path, report_path)
            updated_bugs = self.pmd_analyzer.parse_pmd_xml(report_path)

            # Convert bug_line to integer for comparison
            try:
                bug_line_int = int(bug_line.strip())
            except ValueError:
                bug_line_int = -1

            # Define a range around the original bug line to account for line shifts
            line_range = 10  # Look 10 lines before and after the original line
            min_line = max(1, bug_line_int - line_range)
            max_line = bug_line_int + line_range

            # Find specific bug by rule and general line area
            specific_bug_exists = False
            for bug in updated_bugs:
                bug_rule = bug.get('rule', '').lower()
                bug_type_from_report = bug.get('type', '').lower()
                target_type = bug_type.lower()

                # Check if either rule or type matches
                if bug_rule == target_type or bug_type_from_report == target_type:
                    try:
                        bug_line_in_report = int(bug.get('line', '-1').strip())
                        if min_line <= bug_line_in_report <= max_line:
                            specific_bug_exists = True
                            break
                    except ValueError:
                        continue

            # Get other bugs (excluding the specific bug type we're validating)
            other_bugs = [bug for bug in updated_bugs if bug.get('rule', '').lower() != bug_type.lower()
                          and bug.get('type', '').lower() != bug_type.lower()]

            return {
                'bug_fixed': not specific_bug_exists,
                'other_bugs': other_bugs
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'bug_fixed': False,
                'other_bugs': []
            }
