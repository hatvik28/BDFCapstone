import subprocess
import os
import xml.etree.ElementTree as ET
import tempfile


class PMDAnalyzer:
    def __init__(self, pmd_path: str, ruleset_path: str, report_path: str):
        self.pmd_path = os.path.abspath(pmd_path)
        self.ruleset_path = os.path.abspath(ruleset_path)
        self.report_path = os.path.abspath(report_path)

    def run_pmd_analysis(self, source_file: str, report_path: str = None) -> None:
        if report_path is None:
            report_path = self.report_path

        # Ensure the Java file exists
        if not os.path.exists(source_file):
            return

        # Delete old report if exists
        if os.path.exists(report_path):
            os.remove(report_path)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file_list:
            temp_file_list.write(source_file + "\n")
            temp_file_list_path = temp_file_list.name

        command = [
            self.pmd_path, "check",
            "--file-list", temp_file_list_path,
            "--rulesets", self.ruleset_path,
            "--format", "xml",
            "--report-file", report_path
        ]

        try:
            result = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            if result.returncode != 0 and result.returncode != 4:
                return

        except Exception as e:
            pass

        finally:
            if os.path.exists(temp_file_list_path):
                os.remove(temp_file_list_path)

    def extract_code_snippet(self, file_path: str, line_number: int, bug_description: str) -> str:
        """Extract a code snippet around the bug location."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            # Create a window: 2 lines before + bug line + 2 after
            start = max(0, line_number - 3)
            end = min(len(lines), line_number + 2)
            context_code = "".join(lines[start:end]).strip()

            return context_code

        except Exception as e:
            return ""

    def parse_pmd_xml(self, report_path: str = None) -> list:
        """Parse the PMD report and extract detected issues."""
        if report_path is None:
            report_path = self.report_path

        issues = []

        if not os.path.exists(report_path):
            return issues

        try:
            tree = ET.parse(report_path)
            root = tree.getroot()

            # Extract the namespace URI from the root tag
            ns_uri = root.tag.split('}')[0].strip('{')
            ns = {"pmd": ns_uri}

            for file in root.findall("pmd:file", ns):
                filename = file.get("name")
                file_path = os.path.normpath(filename)

                for violation in file.findall("pmd:violation", ns):
                    line_number = int(violation.get("beginline"))
                    message = violation.text.strip() if violation.text else "No message"
                    ruleset = violation.get("ruleset", "Unknown")
                    rule = violation.get("rule", "Unknown")
                    severity = violation.get("priority", "Unknown")

                    issues.append({
                        "file": file_path,
                        "line": line_number,
                        "category": ruleset,
                        "severity": severity,
                        "type": rule,
                        "description": message
                    })

        except ET.ParseError as e:
            pass
        except Exception as e:
            pass

        return issues
