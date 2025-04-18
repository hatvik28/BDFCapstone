import os
import shutil
import requests
import re
import git
import time
import stat


class CodeFetcher:
    def __init__(self, repo_name, output_dir, token):
        self.repo_name = repo_name
        self.output_dir = output_dir  # This will now be cloned_repo
        self.token = self._validate_token(token)
        self.local_repo_path = None  # path to cloned Git repo
        self.parent_repo_url = None  # path to parent repository
        self.repo = None  # Git repo object

    def _validate_token(self, token: str) -> str:
        """Validate the GitHub token and ensure it has necessary permissions."""
        if not token:
            raise ValueError("GitHub token is required")

        # Test the token with a simple API call
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            response = requests.get(
                "https://api.github.com/user", headers=headers)
            if response.status_code == 401:
                raise ValueError("Invalid GitHub token")
            elif response.status_code == 403:
                raise ValueError("GitHub token lacks necessary permissions")
            elif response.status_code != 200:
                raise ValueError(f"GitHub API error: {response.status_code}")

            # Check rate limits
            remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            if remaining < 10:
                print(
                    f"[WARNING] Low GitHub API rate limit remaining: {remaining}")

            return token
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to validate GitHub token: {str(e)}")

    def cleanup_directory(self, directory):
        """Clean up a directory and its contents."""
        if os.path.exists(directory):
            try:
                # First try to remove .git directory separately
                git_dir = os.path.join(directory, '.git')
                if os.path.exists(git_dir):
                    try:
                        shutil.rmtree(git_dir, ignore_errors=True)
                    except Exception as e:
                        print(
                            f"[WARNING] Failed to remove .git directory: {e}")
                        # Continue with other files even if .git removal fails

                # Add a small delay to allow file handles to be released
                time.sleep(1)

                # Try to remove the rest of the directory
                for root, dirs, files in os.walk(directory, topdown=False):
                    for name in files:
                        try:
                            file_path = os.path.join(root, name)
                            os.chmod(file_path, 0o777)  # Make file writable
                            os.remove(file_path)
                        except Exception:
                            pass

                    for name in dirs:
                        try:
                            dir_path = os.path.join(root, name)
                            # Make directory writable
                            os.chmod(dir_path, 0o777)
                            os.rmdir(dir_path)
                        except Exception as e:
                            print(
                                f"[WARNING] Failed to remove directory {name}: {e}")

                # Try to remove the root directory
                try:
                    os.rmdir(directory)
                except Exception as e:
                    print(f"[WARNING] Failed to remove root directory: {e}")

            except Exception as e:
                print(
                    f"[ERROR] Failed to clean {directory} Please try again: {e}")
                # Don't raise the exception, just log it

    def clone_repo(self):
        """Clone the repository (either forked or user's own)."""
        clone_dir = os.path.join("cloned_repo")

        def force_remove_readonly(func, path, excinfo):
            os.chmod(path, stat.S_IWRITE)
            func(path)

        # Forcefully remove the existing cloned_repo directory
        if os.path.exists(clone_dir):
            print("[CLEANUP] Removing existing cloned_repo...")
            try:
                shutil.rmtree(clone_dir, onerror=force_remove_readonly)
            except Exception as e:
                print(f"[ERROR] Failed to clean cloned_repo: {e}")
                raise RuntimeError(
                    "Failed to clear previous cloned repo folder.")

        # Check if this is a fork or user's own repo
        is_forked = self.is_fork()
        if is_forked:
            print("[INFO] Working with a forked repository")
        else:
            print("[INFO] Working with your own repository")

        # Use HTTPS with token in URL for authentication
        clone_url = f"https://{self.token}:x-oauth-basic@github.com/{self.repo_name}.git"
        print(f"[GIT] Cloning from: {clone_url}")

        try:
            self.repo = git.Repo.clone_from(clone_url, clone_dir)
            self.local_repo_path = clone_dir

            print(f"[GIT] Repo cloned to: {self.local_repo_path}")
            return self.repo
        except git.exc.GitCommandError as e:
            raise RuntimeError(f"Failed to clone repository: {e}")

    def fetch_java_files_from_local_clone(self) -> list:
        """
        After cloning, find all .java files inside the cloned repo
        and return their contents.
        """
        java_files = []

        if not self.local_repo_path or not os.path.exists(self.local_repo_path):
            return {"error": "No local Git repository found."}

        # Walk through the cloned repo
        for root, _, files in os.walk(self.local_repo_path):
            print(f"[INFO] Searching in: {root}")
            for file in files:
                if file.endswith(".java"):
                    full_path = os.path.join(root, file)

                    # Calculate relative path from repo root
                    rel_path = os.path.relpath(full_path, self.local_repo_path)

                    try:
                        # Read the file content
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            java_files.append({
                                "filename": rel_path,
                                "content": content
                            })
                    except Exception as e:
                        print(f"[ERROR] Could not process {file}: {e}")

        print(f"[INFO] Found {len(java_files)} Java files in repository")
        return java_files

    @staticmethod
    def extract_repo_details(github_url):
        """Extract repository details from GitHub URL.

        Args:
            github_url: URL to either:
                - A forked repository
                - User's own repository
                - A specific file in either repository

        Returns:
            tuple: (repo_name, file_path) or (None, None) if invalid
        """
        # Handles both full path to file and general repo URL
        match = re.search(
            r"github\.com/([^/]+)/([^/]+)/blob/(?:main|master)/(.+)", github_url)
        if match:
            owner, repo, file_path = match.groups()
            repo_name = f"{owner}/{repo}"
            return repo_name, file_path

        match = re.search(r"github\.com/([^/]+)/([^/]+)", github_url)
        if match:
            repo_name = f"{match.group(1)}/{match.group(2)}"
            return repo_name, None

        print("[ERROR] Invalid GitHub URL format")
        return None, None

    def setup_upstream(self, original_repo_url: str = None) -> bool:
        """Set up upstream remote for the original repository."""
        try:
            if not self.repo:
                self.repo = git.Repo(self.local_repo_path)

            # If no URL provided and we have parent_repo_url, use that
            if not original_repo_url and hasattr(self, 'parent_repo_url'):
                original_repo_url = self.parent_repo_url

            if not original_repo_url:
                print("[ERROR] No original repository URL provided")
                return False

            if 'upstream' not in self.repo.remotes:
                self.repo.create_remote('upstream', original_repo_url)
                print(f"[GIT] Added upstream remote: {original_repo_url}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to set up upstream: {e}")
            return False

    def is_fork(self) -> bool:
        """Check if the current repository is a fork using GitHub API."""
        try:
            # Extract owner and repo from repo_name
            owner, repo = self.repo_name.split('/')

            # Make API request to check if repository is a fork
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }

            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                repo_data = response.json()
                is_fork = repo_data.get('fork', False)
                if is_fork:
                    print(f"[INFO] Repository {self.repo_name} is a fork")
                    # Store the parent repository URL for later use
                    parent_url = repo_data.get('parent', {}).get('clone_url')
                    if parent_url:
                        print(f"[INFO] Parent repository: {parent_url}")
                        self.parent_repo_url = parent_url
                else:
                    print(f"[INFO] Repository {self.repo_name} is not a fork")
                return is_fork
            else:
                print(
                    f"[ERROR] Failed to check repository status: {response.status_code}")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to check if repository is a fork: {e}")
            return False
