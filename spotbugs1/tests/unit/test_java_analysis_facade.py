import pytest
import os
from unittest.mock import patch, MagicMock
from app.JavaAnalysisFacade import JavaAnalysisFacade


def test_facade_initialization(facade, test_output_dir, test_bin_dir):
    """Test that the facade is properly initialized with all components."""
    assert facade.output_dir == test_output_dir
    assert facade.bin_dir == test_bin_dir
    assert facade.repo_name is None
    assert facade.github_fetcher is not None
    assert facade.spotbugs_analyzer is not None
    assert facade.llm_model is not None
    assert facade.solution_applier is not None
    assert facade.pmd_analyzer is not None
    assert facade.validator is not None
    assert facade.ck_metrics is not None
    assert facade.solution_metrics is not None


def test_analyze_github_repository(facade):
    """Test repository analysis with mocked GitHub interaction."""
    with patch('app.services.CodeFetcher.CodeFetcher.clone_repo') as mock_clone, \
            patch('app.services.CodeFetcher.CodeFetcher.fetch_java_files_from_local_clone') as mock_fetch:

        mock_fetch.return_value = [
            {"filename": "Test.java", "content": "public class Test {}"}
        ]

        result = facade.analyze_github_repository(
            "https://github.com/test/repo")

        assert mock_clone.called
        assert mock_fetch.called
        assert len(result) == 1
        assert result[0]["filename"] == "Test.java"
        assert facade.repo_name == "test/repo"


def test_analyze_file(facade, sample_java_file):
    """Test file analysis with mocked SpotBugs and CK metrics."""
    with patch('app.services.BugAnalyzer.BugAnalyzer.compile_java_files') as mock_compile, \
            patch('app.services.BugAnalyzer.BugAnalyzer.run_spotbugs_analysis') as mock_spotbugs, \
            patch('app.services.BugAnalyzer.BugAnalyzer.parse_spotbugs_xml') as mock_parse, \
            patch('app.services.MetricAnalyzer.CKMetricsAnalyzer.get_original_metrics') as mock_metrics:

        mock_parse.return_value = [
            {
                "file": "Test.java",
                "line": "5",
                "type": "TEST_BUG",
                "description": "Test bug"
            }
        ]
        mock_metrics.return_value = [{"wmc": 1, "cbo": 2, "loc": 10}]

        content, bugs, num_bugs, metrics = facade.analyze_file("Test.java")

        assert mock_compile.called
        assert mock_spotbugs.called
        assert mock_parse.called
        assert mock_metrics.called
        assert len(bugs) == 1
        assert num_bugs == 1
        assert metrics == {"wmc": 1, "cbo": 2, "loc": 10}


def test_generate_bug_solutions(facade, mock_bug_data):
    """Test bug solution generation with mocked LLM."""
    with patch('app.services.LLMModel.LLMModel.generate_solution') as mock_generate, \
            patch('app.services.LLMModel.LLMModel.parse_solutions') as mock_parse, \
            patch('app.services.SolutionApplier.SolutionApplier.apply_solution_to_temp_dir') as mock_apply, \
            patch('app.services.MetricAnalyzer.SolutionMetricsAnalyzer.run_ck_metrics') as mock_ck:

        mock_parse.return_value = [
            {"solution": "System.out.println('fixed');"}
        ]
        mock_apply.return_value = "temp_dir"
        mock_ck.return_value = [{"wmc": 1, "cbo": 2, "loc": 10}]

        solutions = facade.generate_bug_solutions(mock_bug_data, "Test.java")

        assert mock_generate.called
        assert mock_parse.called
        assert mock_apply.called
        assert mock_ck.called
        assert len(solutions) == 1
        assert "ck_metrics" in solutions[0]
        assert "ck_improvements" in solutions[0]


def test_apply_solution(facade, sample_java_file):
    """Test solution application with mocked solution applier."""
    with patch('app.services.SolutionApplier.SolutionApplier.apply_solution') as mock_apply:
        mock_apply.return_value = ("fixed code", "success")

        result = facade.apply_solution(
            sample_java_file,
            "System.out.println('test');",
            "System.out.println('fixed');"
        )

        assert mock_apply.called
        assert result == ("fixed code", "success")


def test_validate_bug(facade):
    """Test bug validation with mocked validator."""
    with patch('app.services.Validator.Validator.validate_bug') as mock_validate:
        mock_validate.return_value = True

        result = facade.validate_bug(
            "Test.java",
            "10",
            "TEST_BUG",
            "original code",
            "patched code"
        )

        assert mock_validate.called
        assert result is True


def test_list_java_files(facade, sample_java_file):
    """Test listing Java files from output directory."""
    files = facade.list_java_files()
    assert len(files) == 1
    assert files[0] == "Test.java"


def test_repository_name_persistence(facade):
    """Test that repository name is properly maintained."""
    with patch('app.services.CodeFetcher.CodeFetcher.clone_repo') as mock_clone, \
            patch('app.services.CodeFetcher.CodeFetcher.fetch_java_files_from_local_clone') as mock_fetch:

        mock_fetch.return_value = []

        # First analysis
        facade.analyze_github_repository("https://github.com/test/repo")
        assert facade.repo_name == "test/repo"

        # Second analysis
        facade.analyze_github_repository("https://github.com/test/repo2")
        assert facade.repo_name == "test/repo2"
