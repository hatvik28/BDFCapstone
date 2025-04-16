import pytest
import os
import shutil
from unittest.mock import patch, MagicMock
from app.services.CodeFetcher import CodeFetcher


@pytest.fixture
def code_fetcher(test_output_dir, mock_github_token):
    """Create a CodeFetcher instance for testing."""
    return CodeFetcher("test/repo", test_output_dir, mock_github_token)


def test_code_fetcher_initialization(code_fetcher, test_output_dir):
    """Test that the CodeFetcher is properly initialized."""
    assert code_fetcher.repo_name == "test/repo"
    assert code_fetcher.output_dir == test_output_dir
    assert code_fetcher.token == "mock_token"
    assert code_fetcher.local_repo_path is None


def test_clear_directory(code_fetcher, test_output_dir):
    """Test directory clearing functionality."""
    # Create some test files
    test_file = os.path.join(test_output_dir, "test.txt")
    test_dir = os.path.join(test_output_dir, "test_dir")
    os.makedirs(test_dir)
    with open(test_file, "w") as f:
        f.write("test")

    # Clear the directory
    code_fetcher.clear_directory(test_output_dir)

    # Check that files are removed but .git is preserved
    assert not os.path.exists(test_file)
    assert not os.path.exists(test_dir)
    assert os.path.exists(os.path.join(test_output_dir, ".git"))


def test_clone_repo(code_fetcher):
    """Test repository cloning with mocked git operations."""
    with patch('git.Repo.clone_from') as mock_clone:
        mock_repo = MagicMock()
        mock_clone.return_value = mock_repo

        result = code_fetcher.clone_repo()

        assert mock_clone.called
        assert result == mock_repo
        assert code_fetcher.local_repo_path == "cloned_repo"
        mock_clone.assert_called_once_with(
            "https://mock_token:x-oauth-basic@github.com/test/repo.git",
            "cloned_repo"
        )


def test_fetch_java_files_from_local_clone(code_fetcher, test_output_dir):
    """Test fetching Java files from cloned repository."""
    # Set up mock repository path
    code_fetcher.local_repo_path = "cloned_repo"

    # Create mock Java files in the cloned repo
    os.makedirs("cloned_repo/src")
    with open("cloned_repo/src/Test.java", "w") as f:
        f.write("public class Test {}")

    result = code_fetcher.fetch_java_files_from_local_clone()

    assert len(result) == 1
    assert result[0]["filename"] == "src/Test.java"
    assert result[0]["content"] == "public class Test {}"

    # Check that file was copied to output directory
    assert os.path.exists(os.path.join(test_output_dir, "src/Test.java"))


def test_extract_repo_details():
    """Test repository details extraction from GitHub URLs."""
    # Test full file path URL
    repo_name, file_path = CodeFetcher.extract_repo_details(
        "https://github.com/test/repo/blob/main/src/Test.java"
    )
    assert repo_name == "test/repo"
    assert file_path == "src/Test.java"

    # Test repository URL
    repo_name, file_path = CodeFetcher.extract_repo_details(
        "https://github.com/test/repo"
    )
    assert repo_name == "test/repo"
    assert file_path is None

    # Test invalid URL
    repo_name, file_path = CodeFetcher.extract_repo_details(
        "https://invalid-url.com"
    )
    assert repo_name is None
    assert file_path is None


def test_sync_output_dir_to_repo(code_fetcher, test_output_dir):
    """Test syncing files back to repository."""
    # Set up mock repository path
    code_fetcher.local_repo_path = "cloned_repo"
    os.makedirs("cloned_repo")

    # Create a test file in output directory
    os.makedirs(os.path.join(test_output_dir, "src"))
    with open(os.path.join(test_output_dir, "src/Test.java"), "w") as f:
        f.write("public class Test {}")

    # Sync files
    code_fetcher.sync_output_dir_to_repo()

    # Check that file was copied to repository
    assert os.path.exists("cloned_repo/src/Test.java")
    with open("cloned_repo/src/Test.java", "r") as f:
        assert f.read() == "public class Test {}"


def test_error_handling(code_fetcher):
    """Test error handling in various scenarios."""
    # Test invalid repository path
    result = code_fetcher.fetch_java_files_from_local_clone()
    assert result == {"error": "No local Git repository found."}

    # Test invalid output directory
    code_fetcher.output_dir = "/invalid/path"
    with pytest.raises(ValueError):
        code_fetcher.sync_output_dir_to_repo()

    # Test invalid repository URL
    repo_name, file_path = CodeFetcher.extract_repo_details("invalid-url")
    assert repo_name is None
    assert file_path is None
