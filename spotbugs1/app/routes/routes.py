from flask import Blueprint, request, jsonify, render_template
from app.JavaAnalysisFacade import JavaAnalysisFacade
from app.config import GITHUB_TOKEN, LLM_API_KEY
import git
import os

# Create blueprint
api_bp = Blueprint('api', __name__)

# Initialize facade
facade = JavaAnalysisFacade(github_token=GITHUB_TOKEN, llm_api_key=LLM_API_KEY)




@api_bp.route('/')
def index():
    return render_template('index.html')



@api_bp.route("/analyze", methods=["POST"])
def analyze_repository():
    """Analyze a GitHub repository."""
    github_url = request.form.get("repo_url")
    if not github_url:
        return jsonify({"error": "No repository URL provided"}), 400

    try:
        java_files = facade.analyze_github_repository(github_url)
        return jsonify({
            "message": "Files fetched successfully.",
            "files": java_files
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/files", methods=["GET"])
def list_files():
    """List all Java files."""
    try:
        files = facade.list_java_files()
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# In the file_content route:
@api_bp.route('/file_content', methods=['POST'])
def get_file_content():
    """Get file content and bugs."""
    data = request.get_json()
    filename = data.get('filename')
    tool = data.get('tool', 'spotbugs')  # Default to spotbugs if not specified

    if not filename:
        return jsonify({"success": False, "error": "Filename not provided"}), 400

    try:
        content, bugs, num_bugs, metrics = facade.analyze_file(filename, tool)

        # Check if an error occurred in analysis
        if isinstance(metrics, dict) and "error" in metrics:
            return jsonify({
                "success": False,
                "error": metrics["error"]
            }), 400  # Use 400 for known failures

        return jsonify({
            "success": True,
            "filename": filename,
            "content": content,
            "bugs": bugs,
            "num_bugs": num_bugs,
            "metrics": metrics,
            "analysis_tool": tool.capitalize()  # Capitalize the tool name
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Unexpected error during file analysis: {str(e)}"
        }), 500


@api_bp.route('/send_to_llm', methods=['POST'])
def generate_solutions():
    """Generate solutions for a bug."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No bug data provided"}), 400

    try:
        bug_info = {"bug": data.get(
            'bug'), "file_content": data.get('file_content')}
        filename = data.get('file_name')
        solutions = facade.generate_bug_solutions(bug_info, filename)
        return jsonify({"solutions": solutions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/update_solution', methods=['POST'])
def update_solution():
    """Update a solution based on user feedback."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Extract required fields
        bug_type = data.get('bug_type')
        description = data.get('description')
        original_code = data.get('original_code')
        current_solution = data.get('current_solution')
        user_feedback = data.get('user_feedback')
        solution_number = data.get('solution_number', 1)
        filename = data.get('filename', 'Unknown.java')

        # Validate required fields
        if not all([bug_type, description, original_code, current_solution, user_feedback]):
            return jsonify({"error": "Missing required fields"}), 400

        # Call LLM model to update solution
        updated_solution = facade.llm_model.update_solution(
            bug_type=bug_type,
            description=description,
            original_code=original_code,
            current_solution=current_solution,
            user_feedback=user_feedback
        )

        # Clear any cached data for this file
        facade.clear_cache_for_file(os.path.basename(filename))

        # Apply the updated solution snippet to the original code
        solution_dir = facade.solution_applier.apply_solution_to_temp_dir(
            original_code=original_code,
            code_snippet=current_solution,  # The snippet we're replacing
            # Use the updated snippet for replacement
            solution=updated_solution['snippet'],
            filename=filename,
            solution_number=solution_number
        )

        # Read the newly created file to get the integrated solution
        temp_file_path = os.path.join(solution_dir, os.path.basename(filename))
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            integrated_solution = f.read()

        # Extract the relevant snippet using GPT
        # Default to the updated solution
        display_snippet = updated_solution['snippet']

        # Only clear this specific solution's metrics from cache
        solution_cache_key = f"{os.path.basename(filename)}_{solution_number}"
        if facade.solution_metrics.metrics_cache.has(solution_cache_key):
            facade.solution_metrics.metrics_cache.clear()

        # Make sure original metrics are refreshed for consistent comparison
        _ = facade.ck_metrics.get_original_metrics(os.path.basename(filename))

        return jsonify({
            # The updated snippet
            "updated_solution": updated_solution['snippet'],
            "full_solution": integrated_solution,  # Full updated file for download/view
            "solution_dir": solution_dir
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route('/apply_solution', methods=['POST'])
def apply_solution():
    """Apply a solution to fix a bug."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No solution data provided"}), 400

    try:
        formatted_code, message, metrics_data = facade.apply_solution(
            data.get('file_path'),
            data.get('code_snippet'),
            data.get('solution'),
            # Default to solution 1 if not specified
            data.get('solution_number', 1)
        )

        return jsonify({
            "corrected_code": formatted_code,
            "message": message,
            "metrics": metrics_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/calculate_metrics', methods=['POST'])
def calculate_metrics():
    """Calculate metrics for a specific solution without applying it."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    filename = data.get('filename')
    solution_number = data.get('solution_number')

    if not filename or not solution_number:
        return jsonify({"error": "Missing filename or solution number"}), 400

    try:
        # Try to get the solution directory
        solution_dir = os.path.join("temp_ck", f"solution_{solution_number}")

        if not os.path.exists(solution_dir):
            return jsonify({"error": f"Solution directory not found: {solution_dir}"}), 404

        # Calculate metrics
        original_metrics_list = facade.ck_metrics.get_original_metrics(
            filename)
        original_metrics = original_metrics_list[0] if original_metrics_list else {
        }

        solution_metrics_list = facade.solution_metrics.calculate_metrics_for_applied_solution(
            filename, solution_dir, solution_number
        )

        solution_metrics = solution_metrics_list[0] if solution_metrics_list else {
        }

        # Calculate improvements
        ck_improvements = {}
        for key in ["wmc", "loc"]:
            before = int(original_metrics.get(key, 0))
            after = int(solution_metrics.get(key, 0))
            ck_improvements[key] = {
                "before": before,
                "after": after,
                "delta": after - before
            }

        metrics_data = {
            "original_metrics": original_metrics,
            "solution_metrics": solution_metrics,
            "improvements": ck_improvements
        }

        return jsonify({"metrics": metrics_data})

    except Exception as e:
        return jsonify({"error": f"Error calculating metrics: {str(e)}"}), 500


@api_bp.route('/validate_patch', methods=['POST'])
def validate_patch():
    try:
        data = request.get_json()

        filename = data.get("filename")
        bug_line = data.get("bug_line")
        bug_type = data.get("bug_type")
        original_code = data.get("original_code")
        patched_code = data.get("patched_code")
        tool = data.get("tool", "spotbugs")

        if not all([filename, bug_line, bug_type, original_code, patched_code]):
            return jsonify({
                "bug_fixed": False,
                "message": "Missing required fields",
                "other_bugs": []
            }), 400

        # Get validation results
        validation_results = facade.validate_bug(
            filename=filename,
            bug_line=bug_line,
            bug_type=bug_type,
            original_code=original_code,
            patched_code=patched_code,
            tool=tool
        )

        is_bug_fixed = validation_results.get('bug_fixed', False)
        # 422 Unprocessable Entity when bug still exists
        status_code = 200 if is_bug_fixed else 422

        return jsonify({
            "bug_fixed": is_bug_fixed,
            "message": "Target bug was successfully fixed" if is_bug_fixed else "Target bug still exists",
            # Keep this for frontend reference but don't show in message
            "other_bugs": validation_results.get('other_bugs', [])
        }), status_code

    except Exception as e:
        error_msg = f"Error during validation: {str(e)}"
        return jsonify({
            "bug_fixed": False,
            "message": error_msg,
            "other_bugs": []
        }), 500


@api_bp.route('/commit_changes', methods=['POST'])
def commit_changes():
    """Commit and push changes to GitHub."""
    try:
        repo_path = facade.github_fetcher.local_repo_path

        if not repo_path or not os.path.exists(repo_path):
            print("[RECOVERY] Attempting to re-clone GitHub repo...")

            if not facade.repo_name:
                print("[ERROR] No repository name found in facade")
                # Try to get the repository URL from the request
                data = request.get_json()
                repo_url = data.get('repo_url')
                if not repo_url:
                    return jsonify({
                        "success": False,
                        "message": "Please provide a repository URL to analyze."
                    }), 400

                try:
                    # Extract repository name from URL using the facade
                    repo_name, _ = facade.github_fetcher.extract_repo_details(
                        repo_url)
                    if not repo_name:
                        return jsonify({
                            "success": False,
                            "message": "Invalid repository URL format."
                        }), 400

                    print(f"[RECOVERY] Setting repository name: {repo_name}")
                    facade.repo_name = repo_name
                    facade.github_fetcher.repo_name = repo_name

                    print(
                        f"[RECOVERY] Attempting to analyze repository: {repo_url}")
                    facade.analyze_github_repository(repo_url)
                    repo_path = facade.github_fetcher.local_repo_path
                    print(f"[RECOVERY] Repository analyzed successfully")
                except Exception as e:
                    print(f"[ERROR] Failed to analyze repository: {str(e)}")
                    return jsonify({
                        "success": False,
                        "message": f"Failed to analyze repository: {str(e)}"
                    }), 500

            try:
                facade.github_fetcher.repo_name = facade.repo_name  # Ensure repo_name is set
                facade.github_fetcher.clone_repo()
                repo_path = facade.github_fetcher.local_repo_path
            except Exception as e:
                return jsonify({
                    "success": False,
                    "message": f"Failed to access repository. Please check your permissions and try again: {e}"
                }), 500

            if not repo_path or not os.path.exists(repo_path):
                return jsonify({
                    "success": False,
                    "message": "Unable to access repository. Please ensure you have the correct permissions and try again."
                }), 400

        data = request.get_json()
        commit_message = data.get(
            'commit_message', 'Automated bug fixes applied')

        # Get the absolute path of the repo
        repo_abs_path = os.path.abspath(repo_path)

        # Initialize git repo
        repo = git.Repo(repo_path)

        # Add all Java files at once using git add with a pattern
        repo.git.add('*.java')

        # Commit and push
        repo.index.commit(commit_message)
        repo.remote(name='origin').push()

        # Clear all metrics caches after successful commit
        if hasattr(facade, 'ck_metrics') and facade.ck_metrics:
            facade.ck_metrics.metrics_cache.clear()
        if hasattr(facade, 'solution_metrics') and facade.solution_metrics:
            facade.solution_metrics.metrics_cache.clear()

        return jsonify({
            "success": True,
            "message": "Changes committed and pushed to GitHub successfully."
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500
