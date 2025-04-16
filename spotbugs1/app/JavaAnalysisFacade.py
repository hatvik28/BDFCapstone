import glob
import os
import json
import re
import shutil
import time
from typing import Dict, List, Tuple, Optional
from app.services.CodeFetcher import CodeFetcher
from app.services.BugAnalyzer import BugAnalyzer
from app.services.LLMModel import LLMModel
from app.services.SolutionApplier import SolutionApplier
from app.services.Validator import Validator
from app.services.PMDAnalyzer import PMDAnalyzer  # PMD re-enabled
from app.services.MetricAnalyzer import CKMetricsAnalyzer
from app.services.MetricAnalyzer import SolutionMetricsAnalyzer
from app.services.MetricAnalyzer import organize_ck_outputs
from app.services.BuildSystemManager import BuildSystemManager
from app.config import OUTPUT_DIR, GITHUB_TOKEN, BIN_DIR, SPOTBUGS_PATH, SPOTBUGS_REPORT_PATH, GOOGLE_FORMATTER_PATH, REPO_ROOT_DIR, PMD_PATH, PMD_RULESET_PATH, PMD_REPORT_PATH  # Added PMD paths


class JavaAnalysisFacade:
    def __init__(self,
                 github_token: str = GITHUB_TOKEN,
                 output_dir: str = OUTPUT_DIR,
                 bin_dir: str = BIN_DIR,
                 spotbugs_path: str = SPOTBUGS_PATH,
                 pmd_path: str = PMD_PATH,  # PMD re-enabled
                 pmd_ruleset_path: str = PMD_RULESET_PATH,
                 pmd_report_path: str = PMD_REPORT_PATH,
                 llm_api_key: Optional[str] = None):
        """Initialize the facade with all necessary components."""

        self.output_dir = output_dir
        self.bin_dir = bin_dir
        self.repo_name = None  # Store repository name

        # Clean bin directory on initialization
        self._clean_bin_directory()

        # Initialize components
        self.github_fetcher = CodeFetcher(
            self.repo_name, output_dir, github_token)
        self.spotbugs_analyzer = BugAnalyzer(
            output_dir, bin_dir, spotbugs_path, REPO_ROOT_DIR)
        self.llm_model = LLMModel(llm_api_key) if llm_api_key else None
        self.solution_applier = SolutionApplier(GOOGLE_FORMATTER_PATH)
        self.pmd_analyzer = PMDAnalyzer(  # PMD re-enabled
            pmd_path, pmd_ruleset_path, pmd_report_path)
        self.build_system_manager = BuildSystemManager(
            output_dir, bin_dir, spotbugs_path, REPO_ROOT_DIR)
        self.validator = Validator(
            output_dir, bin_dir, spotbugs_path, self.spotbugs_analyzer,
            self.pmd_analyzer, self.build_system_manager)  # Added build_system_manager
        self.ck_metrics = CKMetricsAnalyzer()
        self.solution_metrics = SolutionMetricsAnalyzer()
        # Load bug descriptions
        self.bug_descriptions = self._load_bug_descriptions()

        # Add cache for bugs and metrics
        self._bugs_cache = {}
        self._metrics_cache = {}
        self._last_analysis_time = {}
        self._cache_timeout = 300  # 5 minutes cache timeout

        # Add persistent cache for initial metrics
        self._initial_metrics_cache = {}

    def _clean_bin_directory(self):
        """Clean the bin directory by removing all .class files and subdirectories."""
        try:
            if os.path.exists(self.bin_dir):
                print(f"[CLEANUP] Cleaning bin directory: {self.bin_dir}")
                # Remove all files and subdirectories in the bin directory
                for root, dirs, files in os.walk(self.bin_dir, topdown=False):
                    # First remove all files
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            print(
                                f"[WARNING] Failed to remove file {file_path}: {e}")

                    # Then remove all directories (except the root bin directory)
                    for dir in dirs:
                        dir_path = os.path.join(root, dir)
                        try:
                            os.rmdir(dir_path)
                        except Exception as e:
                            print(
                                f"[WARNING] Failed to remove directory {dir_path}: {e}")
        except Exception as e:
            print(f"[ERROR] Failed to clean bin directory: {e}")

    def analyze_github_repository(self, github_url: str) -> List[Dict]:
        """Fetch Java files from a GitHub repository."""
        # Extract repository details
        repo_name, file_path = CodeFetcher.extract_repo_details(github_url)
        if not repo_name:
            raise ValueError("Invalid GitHub URL")

        # Store repository name
        self.repo_name = repo_name

        # Update fetcher with new repo name
        self.github_fetcher.repo_name = repo_name

        # Clear and prepare directories
        self.github_fetcher.cleanup_directory(self.output_dir)
        self._clean_bin_directory()  # Clean bin directory before cloning new repo

        # Clone the repository
        self.github_fetcher.clone_repo()

        # Check if it's a fork and set up upstream if needed
        if self.github_fetcher.is_fork():
            print("[INFO] Setting up upstream remote for forked repository")
            if not self.github_fetcher.setup_upstream():
                print("[WARNING] Failed to set up upstream remote")

        # Clear the initial metrics cache when analyzing a new repo
        self._initial_metrics_cache.clear()
        print("[CACHE] Cleared initial metrics cache for new repository analysis.")

        # Fetch files
        return self.github_fetcher.fetch_java_files_from_local_clone()

    def analyze_file(self, filename: str, tool: str = 'spotbugs') -> Tuple[str, List[Dict], int, List[Dict]]:
        """Analyze a Java file for bugs using the specified tool."""
        print(PMD_PATH)
        try:
            # Get file content first
            file_path = os.path.join(self.output_dir, filename)
            with open(file_path, 'r') as f:
                content = f.read()

            # Generate unique report paths for each file and tool
            report_filename = f"{tool}_report_{os.path.basename(filename)}.xml"
            report_path = os.path.join(self.output_dir, report_filename)

            # Check if we need to compile (do this before cache check)
            needs_compilation = tool.lower() == 'spotbugs'
            if needs_compilation:
                rel_path = os.path.relpath(file_path, self.output_dir)
                class_file = os.path.join(
                    self.bin_dir, rel_path.replace('.java', '.class'))

                # Only recompile if class file doesn't exist
                if not os.path.exists(class_file):
                    print(
                        f"[INFO] Class file not found, compiling {file_path}")
                    try:
                        if not self.build_system_manager.compile_java_files(file_path, self.bin_dir):
                            error_msg = "Compilation failed. Cannot proceed with SpotBugs analysis."
                            print(f"[ERROR] {error_msg}")
                            return content, [], 0, []
                    except RuntimeError as e:
                        error_msg = str(e)
                        print(f"[ERROR] {error_msg}")
                        return content, [], 0, []

            # Check cache after compilation
            cached_bugs, cached_metrics = self._get_cached_data(filename, tool)
            if cached_bugs is not None:
                return content, cached_bugs, len(cached_bugs), cached_metrics

            # Handle different analysis tools
            if tool.lower() == 'pmd':
                print(f"[INFO] Running PMD analysis on {file_path}")
                self.pmd_analyzer.run_pmd_analysis(
                    source_file=file_path, report_path=report_path)
                bugs = self._get_file_bugs_pmd(filename, report_path)
            else:  # SpotBugs
                print("[INFO] Running SpotBugs analysis")
                self.spotbugs_analyzer.run_spotbugs_analysis(report_path)
                bugs = self._get_file_bugs(filename, report_path)

            num_bugs = len(bugs)

            # Get metrics - Check initial cache first
            base_filename = os.path.basename(filename)
            if base_filename in self._initial_metrics_cache:
                print(
                    f"[CACHE] Using initial metrics from cache for {base_filename}")
                metrics = self._initial_metrics_cache[base_filename]
            else:
                print(
                    f"[METRICS] Calculating initial metrics for {base_filename}")
                metrics_list = self.ck_metrics.get_original_metrics(
                    filename)  # filename has path needed by CK
                metrics = metrics_list[0] if metrics_list else {}
                if metrics and "error" not in metrics:
                    print(
                        f"[CACHE] Storing initial metrics for {base_filename}")
                    # Store in persistent cache
                    self._initial_metrics_cache[base_filename] = metrics
                else:
                    print(
                        f"[WARNING] Failed to calculate or invalid initial metrics for {base_filename}")
                    # Ensure error state if calculation fails
                    metrics = {"error": "Failed to calculate initial metrics"}

            print("[CKMetricsAnalyzer] Metrics Found:", metrics)

            # Cache the results for time-based expiration
            self._update_cache(filename, bugs, metrics, tool)

            # Ensure metrics is returned as a list to match frontend expectations
            metrics_to_return = [
                metrics] if metrics and "error" not in metrics else []
            return content, bugs, num_bugs, metrics_to_return

        except Exception as e:
            error_msg = f"Unexpected error during analysis: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return "", [], 0, []

    def generate_bug_solutions(self, bug_info: Dict, filename: str) -> List[Dict]:
        """Generates solutions for bugs using LLM without calculating metrics."""
        if not self.llm_model:
            raise ValueError("LLM API key not provided")

        # Create temp directories if needed
        os.makedirs("temp_ck", exist_ok=True)
        os.makedirs("ck_output_solutions", exist_ok=True)

        file_content = bug_info.get("file_content")
        bug = bug_info.get("bug", {})
        code_snippet = bug.get("code_snippet")

        print(f"[INFO] Generating solutions for bug in {filename}")

        # Generate LLM fixes
        raw_response = self.llm_model.generate_solution(
            bug.get("type"),
            bug.get("description"),
            bug.get("line"),
            code_snippet,
            file_content
        )

        solutions = self.llm_model.parse_solutions(raw_response)
        if not solutions:
            return []

        # Apply each solution to a temp file (without metrics calculation)
        for i, sol in enumerate(solutions):
            try:
                # Apply fix to a temp file
                solution_dir = self.solution_applier.apply_solution_to_temp_dir(
                    original_code=file_content,
                    code_snippet=code_snippet,
                    solution=sol["solution"],
                    filename=filename,
                    solution_number=i + 1
                )

                # Store the solution directory for later metrics calculation
                sol["solution_dir"] = solution_dir
                sol["solution_number"] = i + 1

            except Exception as e:
                print(f"[ERROR] Failed to apply solution to temp dir: {e}")
                sol["solution_dir"] = None
                sol["error"] = str(e)

        print(f"[INFO] Generated {len(solutions)} solutions for {filename}")
        return solutions

    def apply_solution(self, file_path: str, code_snippet: str, solution: str, solution_number: int = 1) -> Tuple[str, str, Dict]:
        """Apply a solution to fix a bug and calculate metrics for it."""
        try:
            # Get the filename
            filename = os.path.basename(file_path)

            # Clear ALL caches for this file before applying the solution
            print(f"[DEBUG] Clearing caches for file: {filename}")
            self.clear_cache_for_file(filename)

            # Print debug info about what we're applying
            print(
                f"[DEBUG] Applying solution {solution_number} to {file_path}")
            print(
                f"[DEBUG] Code snippet to replace (first 100 chars): {code_snippet[:100]}...")
            print(
                f"[DEBUG] Solution to apply (first 100 chars): {solution[:100]}...")

            # Apply the solution
            formatted_code, message = self.solution_applier.apply_solution(
                file_path, code_snippet, solution, solution_number)

            # Calculate metrics for the applied solution
            solution_dir = os.path.join(
                "temp_ck", f"solution_{solution_number}")
            metrics_data = {}

            try:
                # Retrieve initial metrics from the persistent cache
                initial_metrics = self._initial_metrics_cache.get(filename, {})
                if not initial_metrics:
                    print(
                        f"[WARNING] Initial metrics not found in cache for {filename}. Comparison might be inaccurate.")
                    # As a fallback, calculate current metrics before apply (less ideal)
                    metrics_list = self.ck_metrics.get_original_metrics(
                        filename)
                    initial_metrics = metrics_list[0] if metrics_list else {}

                print(
                    f"[DEBUG] Using Initial metrics for comparison: LOC={initial_metrics.get('loc', 'N/A')}")

                # Get metrics for the applied solution ("After" state)
                solution_metrics_list = self.solution_metrics.calculate_metrics_for_applied_solution(
                    filename, solution_dir, solution_number
                )
                solution_metrics = solution_metrics_list[0] if solution_metrics_list else {
                }
                print(
                    f"[DEBUG] Solution {solution_number} metrics ('After'): LOC={solution_metrics.get('loc', 'N/A')}")

                # Calculate improvements comparing INITIAL vs APPLIED
                ck_improvements = {}
                for key in ["wmc", "loc"]:
                    # Use initial_metrics for 'before'
                    before = int(initial_metrics.get(key, 0))
                    # Use solution_metrics for 'after'
                    after = int(solution_metrics.get(key, 0))
                    ck_improvements[key] = {
                        "before": before,  # Represents the initial state
                        "after": after,   # Represents the state after this fix
                        "delta": after - before  # Change from initial state
                    }

                metrics_data = {
                    "original_metrics": initial_metrics,  # Now represents the true original
                    "solution_metrics": solution_metrics,  # State after current fix
                    "improvements": ck_improvements  # Comparison between initial and current fix
                }

            except Exception as e:
                print(
                    f"[ERROR] Failed to calculate metrics for applied solution: {e}")
                metrics_data = {
                    "error": str(e),
                    "original_metrics": {},
                    "solution_metrics": {},
                    "improvements": {}
                }

            return formatted_code, message, metrics_data

        except Exception as e:
            print(f"[ERROR] Failed to apply solution: {str(e)}")
            return "", f"Error applying solution: {str(e)}", {"error": str(e)}

    def validate_bug(self, filename: str, bug_line: str, bug_type: str, original_code: str = None, patched_code: str = None, tool: str = 'spotbugs') -> dict:
        """
        Validate if a specific bug has been fixed, while also checking for other bugs.

        Returns a dictionary containing:
        - bug_fixed: bool - Whether the specific bug was fixed
        - other_bugs: list - Any remaining bugs in the file
        - validation_message: str - Human readable message about the validation
        """
        try:
            # Get validation results from validator
            validation_results = self.validator.validate_bug(
                filename=filename,
                bug_line=bug_line,
                bug_type=bug_type,
                bug_descriptions=self.bug_descriptions,
                original_code=original_code,
                patched_code=patched_code,
                tool=tool
            )

            # Extract results
            bug_fixed = validation_results['bug_fixed']
            other_bugs = validation_results['other_bugs']

            # Construct appropriate message
            message_parts = []
            if bug_fixed:
                message_parts.append("Target bug was successfully fixed")
            else:
                message_parts.append("Target bug still exists")

            if other_bugs:
                message_parts.append(
                    f"{len(other_bugs)} other bugs remain in the file")

            return {
                'success': bug_fixed,  # Consider the validation successful if the target bug is fixed
                'bug_fixed': bug_fixed,
                'other_bugs': other_bugs,
                'validation_message': ". ".join(message_parts)
            }

        except Exception as e:
            print(f"[ERROR] Validation failed: {str(e)}")
            return {
                'success': False,
                'bug_fixed': False,
                'other_bugs': [],
                'validation_message': f"Validation failed: {str(e)}"
            }

    def list_java_files(self) -> List[str]:
        """List all Java files in the output directory."""
        files = []
        for root, _, filenames in os.walk(self.output_dir):
            for filename in filenames:
                if filename.endswith(".java"):
                    files.append(os.path.relpath(
                        os.path.join(root, filename), self.output_dir))
        return files

    def _normalize_file_path(self, file_path: str) -> str:
        """Normalize a file path to handle different formats."""
        # Remove any leading/trailing slashes and convert to lowercase
        normalized = file_path.strip().lower()

        # If it's just a filename, return it
        if not os.path.sep in normalized:
            return normalized

        # If it's a full path, get just the filename
        return os.path.basename(normalized)

    def _get_file_bugs(self, filename: str, report_path: str) -> List[Dict]:
        """Internal method to get bugs for a specific file from SpotBugs."""
        # Check cache first
        cached_bugs, _ = self._get_cached_data(filename, 'spotbugs')
        if cached_bugs is not None:
            return cached_bugs

        try:
            # Try SpotBugs
            all_bugs = self.spotbugs_analyzer.parse_spotbugs_xml(
                report_path, self.bug_descriptions
            )
        except Exception as e:
            print(f"[WARN] Failed to parse SpotBugs results: {str(e)}")
            return []

        # Filter bugs by filename - handle different path formats
        file_bugs = []
        normalized_filename = self._normalize_file_path(filename)

        for bug in all_bugs:
            bug_file = bug["file"]
            normalized_bug_file = self._normalize_file_path(bug_file)

            if normalized_bug_file == normalized_filename:
                file_bugs.append(bug)

        # Add code snippets
        for bug in file_bugs:
            bug_line = int(bug["line"])
            bug_description = bug.get(
                "description", "No description available")
            file_path = os.path.join(self.output_dir, filename)

            bug["code_snippet"] = self.spotbugs_analyzer.extract_code_snippet(
                file_path=file_path,
                line_number=bug_line,
                bug_description=bug_description
            )

        # Cache the results
        self._update_cache(filename, file_bugs, {}, 'spotbugs')
        return file_bugs

    def _get_file_bugs_pmd(self, filename: str, report_path: str) -> List[Dict]:
        """Internal method to get bugs for a specific file from PMD."""
        # Check cache first
        cached_bugs, _ = self._get_cached_data(filename, 'pmd')
        if cached_bugs is not None:
            return cached_bugs

        try:
            # Parse the results
            all_bugs = self.pmd_analyzer.parse_pmd_xml(report_path=report_path)
        except Exception as e:
            print(f"[WARN] Failed to parse PMD results: {str(e)}")
            return []

        # Filter bugs by filename - handle different path formats
        file_bugs = []
        normalized_filename = self._normalize_file_path(filename)

        for bug in all_bugs:
            bug_file = bug["file"]
            normalized_bug_file = self._normalize_file_path(bug_file)

            if normalized_bug_file == normalized_filename:
                file_bugs.append(bug)

        # Add code snippets
        for bug in file_bugs:
            bug_line = int(bug["line"])
            bug_description = bug.get(
                "description", "No description available")
            file_path = os.path.join(self.output_dir, filename)

            bug["code_snippet"] = self.pmd_analyzer.extract_code_snippet(
                file_path=file_path,
                line_number=bug_line,
                bug_description=bug_description
            )

        # Cache the results
        self._update_cache(filename, file_bugs, {}, 'pmd')
        return file_bugs

    def _load_bug_descriptions(self) -> Dict:
        """Load bug descriptions from JSON file."""
        bug_descriptions_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "bug_descriptions.json"
        )
        try:
            with open(bug_descriptions_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"ERROR: Failed to load bug descriptions - {e}")
            return {}


    def _is_cache_valid(self, filename: str, tool: str = 'spotbugs') -> bool:
        """Check if the cached data for a file is still valid."""
        cache_key = f"{filename}_{tool}"
        if cache_key not in self._last_analysis_time:
            return False
        current_time = time.time()
        return (current_time - self._last_analysis_time[cache_key]) < self._cache_timeout

    def _update_cache(self, filename: str, bugs: List[Dict], metrics: Dict, tool: str = 'spotbugs'):
        """Update the cache with new bugs and metrics data."""
        cache_key = f"{filename}_{tool}"
        self._bugs_cache[cache_key] = bugs
        self._metrics_cache[cache_key] = metrics
        self._last_analysis_time[cache_key] = time.time()

    def _get_cached_data(self, filename: str, tool: str = 'spotbugs') -> Tuple[List[Dict], Dict]:
        """Get cached bugs and metrics data if available and valid."""
        cache_key = f"{filename}_{tool}"
        if self._is_cache_valid(filename, tool):
            return self._bugs_cache.get(cache_key, []), self._metrics_cache.get(cache_key, {})
        return None, None

    def clear_cache_for_file(self, filename: str):
        """Clear time-based cached data for a specific file, leaving initial metrics intact."""
        print(f"[INFO] Clearing time-based cache for file: {filename}")
        # Use base filename for consistency
        base_filename = os.path.basename(filename)

        # Clear bug analysis cache for different tools
        for tool in ['spotbugs', 'pmd']:
            # Key format used in _update_cache
            cache_key = f"{base_filename}_{tool}"
            if cache_key in self._bugs_cache:
                del self._bugs_cache[cache_key]
                print(f"[CACHE] Removed bugs cache for {cache_key}")
            if cache_key in self._metrics_cache:  # Clear time-based metrics cache
                del self._metrics_cache[cache_key]
                print(
                    f"[CACHE] Removed time-based metrics cache for {cache_key}")
            if cache_key in self._last_analysis_time:
                del self._last_analysis_time[cache_key]
                print(f"[CACHE] Removed last analysis time for {cache_key}")

        # We specifically DO NOT clear self._initial_metrics_cache here
        print(f"[INFO] Time-based cache cleared for file: {base_filename}")
