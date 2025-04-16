import pytest
import os
from unittest.mock import patch, MagicMock
from app.services.SolutionApplier import SolutionApplier


@pytest.fixture
def solution_applier(mock_google_formatter_path):
    """Create a SolutionApplier instance for testing."""
    return SolutionApplier(mock_google_formatter_path)


@pytest.fixture
def sample_java_code():
    """Provide sample Java code for testing."""
    return """
public class Test {
    public static void main(String[] args) {
        System.out.println("test");
    }
}
"""


def test_solution_applier_initialization(solution_applier, mock_google_formatter_path):
    """Test that the SolutionApplier is properly initialized."""
    assert solution_applier.google_formatter_path == mock_google_formatter_path


def test_find_and_replace_buggy_code(solution_applier):
    """Test code replacement using ChatGPT."""
    with patch('openai.ChatCompletion.create') as mock_openai:
        mock_openai.return_value = {
            'choices': [{
                'message': {
                    'content': """
```java
public class Test {
    public static void main(String[] args) {
        System.out.println("fixed");
    }
}
```
"""
                }
            }]
        }

        result = solution_applier.find_and_replace_buggy_code(
            "public class Test { public static void main(String[] args) { System.out.println('test'); } }",
            "System.out.println('test');",
            "System.out.println('fixed');"
        )

        assert mock_openai.called
        assert "System.out.println('fixed')" in result
        assert "System.out.println('test')" not in result


def test_apply_solution(solution_applier, sample_java_code, tmp_path):
    """Test solution application to a file."""
    # Create a temporary file
    file_path = tmp_path / "Test.java"
    with open(file_path, "w") as f:
        f.write(sample_java_code)

    # Create a temporary solution directory
    solution_dir = tmp_path / "temp_ck" / "solution_1"
    solution_dir.mkdir(parents=True)

    # Create the solution file
    solution_file = solution_dir / "Test.java"
    with open(solution_file, "w") as f:
        f.write(sample_java_code.replace("test", "fixed"))

    # Apply the solution
    result = solution_applier.apply_solution(
        str(file_path),
        "System.out.println('test');",
        "System.out.println('fixed');"
    )

    assert result[0] == sample_java_code.replace("test", "fixed")
    assert result[1] == "Bug fixed successfully!"


def test_apply_solution_to_temp_dir(solution_applier, sample_java_code, tmp_path):
    """Test applying solution to a temporary directory."""
    # Create a temporary file
    file_path = tmp_path / "Test.java"
    with open(file_path, "w") as f:
        f.write(sample_java_code)

    # Apply solution to temp directory
    solution_dir = solution_applier.apply_solution_to_temp_dir(
        sample_java_code,
        "System.out.println('test');",
        "System.out.println('fixed');",
        "Test.java",
        1
    )

    # Check that solution directory was created
    assert os.path.exists(solution_dir)

    # Check that solution file was created
    solution_file = os.path.join(solution_dir, "Test.java")
    assert os.path.exists(solution_file)

    # Check file contents
    with open(solution_file, "r") as f:
        content = f.read()
        assert "System.out.println('fixed')" in content
        assert "System.out.println('test')" not in content


def test_error_handling(solution_applier):
    """Test error handling in various scenarios."""
    # Test with invalid file path
    with pytest.raises(FileNotFoundError):
        solution_applier.apply_solution(
            "/invalid/path/Test.java",
            "test code",
            "fixed code"
        )

    # Test with no changes made
    with pytest.raises(ValueError):
        solution_applier.apply_solution_to_temp_dir(
            "public class Test {}",
            "test code",
            "test code",  # Same as original
            "Test.java",
            1
        )


def test_code_formatting(solution_applier, sample_java_code, tmp_path):
    """Test code formatting after solution application."""
    with patch('subprocess.run') as mock_subprocess:
        # Create a temporary file
        file_path = tmp_path / "Test.java"
        with open(file_path, "w") as f:
            f.write(sample_java_code)

        # Apply solution
        solution_applier.apply_solution_to_temp_dir(
            sample_java_code,
            "System.out.println('test');",
            "System.out.println('fixed');",
            "Test.java",
            1
        )

        # Check that formatter was called
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0][0]
        assert args[0] == "java"
        assert args[1] == "-jar"
        assert args[2] == solution_applier.google_formatter_path
        assert args[3] == "-i"
