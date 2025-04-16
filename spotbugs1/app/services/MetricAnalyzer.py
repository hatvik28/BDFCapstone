import os
import subprocess
import csv
import shutil
import glob
import re
from app.config import BASE_DIR


class MetricsCache:
    """Cache for storing metrics to avoid redundant calculations."""

    def __init__(self):
        self._cache = {}

    def get(self, key):
        """Get cached metrics for a given key."""
        return self._cache.get(key)

    def set(self, key, metrics):
        """Store metrics in the cache."""
        self._cache[key] = metrics

    def has(self, key):
        """Check if metrics exist in cache."""
        return key in self._cache

    def clear(self):
        """Clear the cache."""
        self._cache.clear()

    def generate_key(self, filename, solution_number):
        """Generate a unique cache key based on filename and solution number."""
        return f"{filename}_{solution_number}"


# Global instance of the metrics cache
metrics_cache = MetricsCache()


def organize_ck_outputs(output_root="ck_output_solutions"):
    """Move CK output files into their respective solution folders."""
    # Find all solution_*class.csv files in the root
    for file_path in glob.glob(os.path.join(output_root, "solution_*class.csv")):
        filename = os.path.basename(file_path)
        match = re.match(r"(solution_\d+)class\.csv", filename)
        if not match:
            continue

        solution_folder = os.path.join(output_root, match.group(1))
        os.makedirs(solution_folder, exist_ok=True)

        # Move the class CSV file
        dest_path = os.path.join(solution_folder, "ck_outputclass.csv")
        try:
            shutil.move(file_path, dest_path)
        except Exception:
            pass

        # Move the corresponding method CSV file
        method_file = file_path.replace("class.csv", "method.csv")
        if os.path.exists(method_file):
            method_dest = os.path.join(solution_folder, "ck_outputmethod.csv")
            try:
                shutil.move(method_file, method_dest)
            except Exception:
                pass


class BaseCKAnalyzer:
    def __init__(self, ck_jar_path=None):
        self.ck_jar_path = ck_jar_path or os.path.abspath(os.path.join(
            BASE_DIR, '..', 'tools', 'ck', 'CKMetrics.jar'))

    def run_ck_metrics(self, source_dir, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        cmd = [
            "java", "-jar",
            self.ck_jar_path,
            os.path.abspath(source_dir),
            "false",
            "0",
            "false",
            os.path.abspath(output_dir)
        ]

        try:
            subprocess.run(cmd, check=True)
            generated_csv = next(
                (os.path.join(root, file)
                 for root, _, files in os.walk(os.getcwd())
                 for file in files
                 if file == "ck_outputclass.csv"),
                None
            )

            if generated_csv:
                dest_csv = os.path.join(output_dir, "ck_outputclass.csv")
                shutil.move(generated_csv, dest_csv)
                return self._parse_class_metrics(output_dir)
            else:
                return []

        except subprocess.CalledProcessError:
            return []

    def _parse_class_metrics(self, output_dir):
        class_metrics_path = os.path.join(output_dir, "ck_outputclass.csv")

        if not os.path.isfile(class_metrics_path):
            return []

        with open(class_metrics_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            return list(reader)

    def get_metrics_for_file(self, filename, source_dir, output_dir):
        all_metrics = self.run_ck_metrics(source_dir, output_dir)
        target_file = os.path.basename(filename).strip().lower()
        # Remove extension to get class name
        target_class = os.path.splitext(target_file)[0]

        matches = []
        primary_matches = []  # For classes that match the filename

        for row in all_metrics:
            file_path = row.get("file", "")
            class_name = row.get("class", "")
            type_name = row.get("type", "").lower()

            base = os.path.basename(file_path).strip().lower()

            if (
                base == target_file and
                type_name == "class" and
                "$" not in class_name  # Exclude anonymous/inner classes
            ):
                # Check if class name matches the filename (case-insensitive)
                if class_name.lower() == target_class:
                    primary_matches.append(row)
                else:
                    matches.append(row)

        # Return priority matches first (classes matching filename), then other matches
        # This ensures the frontend gets the matching class first
        return primary_matches + matches


class CKMetricsAnalyzer(BaseCKAnalyzer):
    def __init__(self):
        super().__init__()
        self.src_dir = os.path.abspath(
            os.path.join(BASE_DIR, '..', '..', 'cloned_repo'))
        self.output_dir = os.path.abspath(
            os.path.join(BASE_DIR, '..', '..', 'ck_output'))
        self.metrics_cache = MetricsCache()  # Initialize own cache instance

    def get_original_metrics(self, filename):
        """Get metrics for the original file."""
        # Check cache first
        cache_key = self.metrics_cache.generate_key(filename, "original")
        cached_metrics = self.metrics_cache.get(cache_key)
        if cached_metrics:
            return cached_metrics

        # Calculate metrics if not cached
        metrics = self.get_metrics_for_file(
            filename, self.src_dir, self.output_dir)

        # Cache the results
        if metrics:
            self.metrics_cache.set(cache_key, metrics)

        return metrics


class SolutionMetricsAnalyzer(BaseCKAnalyzer):
    def __init__(self):
        super().__init__()
        self.metrics_cache = MetricsCache()  # Initialize own cache instance

    def calculate_metrics_for_applied_solution(self, filename, solution_dir, solution_number):
        """Calculate metrics for an applied solution."""
        # Create output folder for metrics
        solution_output_dir = os.path.join(
            "ck_output_solutions", f"solution_{solution_number}")
        os.makedirs(solution_output_dir, exist_ok=True)

        # Check cache first
        cache_key = self.metrics_cache.generate_key(filename, solution_number)
        cached_metrics = self.metrics_cache.get(cache_key)
        if cached_metrics:
            return cached_metrics

        # Run CK metrics if not cached
        self.run_ck_metrics(solution_dir, solution_output_dir)

        # Organize CK output files
        organize_ck_outputs()

        # Parse metrics
        metrics = self._parse_class_metrics(solution_output_dir)

        # Filter metrics for the specific file
        filename_lower = os.path.basename(filename).strip().lower()
        file_metrics = []

        for row in metrics:
            file_path = row.get("file", "")
            base = os.path.basename(file_path).strip().lower()

            if base == filename_lower and row.get("type", "").lower() == "class":
                file_metrics.append(row)

        # Cache the results
        if file_metrics:
            self.metrics_cache.set(cache_key, file_metrics)

        return file_metrics

