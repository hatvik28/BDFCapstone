import pytest
import os
import shutil
from app.JavaAnalysisFacade import JavaAnalysisFacade
from app.services.CodeFetcher import CodeFetcher
from app.services.BugAnalyzer import BugAnalyzer
from app.services.LLMModel import LLMModel
from app.services.SolutionApplier import SolutionApplier
from app.services.Validator import Validator
from app.services.PMDAnalyzer import PMDAnalyzer
from app.services.MetricAnalyzer import CKMetricsAnalyzer
from app.services.MetricAnalyzer import SolutionMetricsAnalyzer


@pytest.fixture
def test_output_dir(tmp_path):
    """Create a temporary output directory for tests."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return str(output_dir)


@pytest.fixture
def test_bin_dir(tmp_path):
    """Create a temporary bin directory for tests."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    return str(bin_dir)


@pytest.fixture
def mock_github_token():
    """Provide a mock GitHub token for testing."""
    return "mock_token"


@pytest.fixture
def mock_llm_api_key():
    """Provide a mock LLM API key for testing."""
    return "mock_llm_key"


@pytest.fixture
def sample_java_file(test_output_dir):
    """Create a sample Java file for testing."""
    file_path = os.path.join(test_output_dir, "Test.java")
    with open(file_path, "w") as f:
        f.write("""
public class Test {
    public static void main(String[] args) {
        System.out.println("Hello World");
    }
}
""")
    return file_path


@pytest.fixture
def mock_spotbugs_path():
    """Provide a mock SpotBugs path for testing."""
    return "mock_spotbugs_path"


@pytest.fixture
def mock_pmd_path():
    """Provide a mock PMD path for testing."""
    return "mock_pmd_path"


@pytest.fixture
def mock_pmd_ruleset_path():
    """Provide a mock PMD ruleset path for testing."""
    return "mock_pmd_ruleset_path"


@pytest.fixture
def mock_pmd_report_path():
    """Provide a mock PMD report path for testing."""
    return "mock_pmd_report_path"


@pytest.fixture
def mock_google_formatter_path():
    """Provide a mock Google formatter path for testing."""
    return "mock_google_formatter_path"


@pytest.fixture
def facade(test_output_dir, test_bin_dir, mock_github_token, mock_llm_api_key,
           mock_spotbugs_path, mock_pmd_path, mock_pmd_ruleset_path,
           mock_pmd_report_path, mock_google_formatter_path):
    """Create a JavaAnalysisFacade instance for testing."""
    return JavaAnalysisFacade(
        github_token=mock_github_token,
        output_dir=test_output_dir,
        bin_dir=test_bin_dir,
        spotbugs_path=mock_spotbugs_path,
        pmd_path=mock_pmd_path,
        pmd_ruleset_path=mock_pmd_ruleset_path,
        pmd_report_path=mock_pmd_report_path,
        llm_api_key=mock_llm_api_key
    )


@pytest.fixture
def mock_bug_data():
    """Provide mock bug data for testing."""
    return {
        "bug": {
            "type": "TEST_BUG",
            "description": "Test bug description",
            "line": "10",
            "code_snippet": "System.out.println('test');"
        },
        "file_content": """
public class Test {
    public static void main(String[] args) {
        System.out.println('test');
    }
}
"""
    }
