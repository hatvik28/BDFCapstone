import pytest
import os
from unittest.mock import patch, MagicMock
from app.services.MetricAnalyzer import BaseCKAnalyzer, CKMetricsAnalyzer, SolutionMetricsAnalyzer
import shutil


@pytest.fixture
def base_analyzer():
    """Create a BaseCKAnalyzer instance for testing."""
    return BaseCKAnalyzer()


@pytest.fixture
def ck_metrics_analyzer():
    """Create a CKMetricsAnalyzer instance for testing."""
    return CKMetricsAnalyzer()


@pytest.fixture
def solution_metrics_analyzer():
    """Create a SolutionMetricsAnalyzer instance for testing."""
    return SolutionMetricsAnalyzer()


@pytest.fixture
def sample_java_file(tmp_path):
    """Create a sample Java file with known metrics."""
    java_content = """
    public class TestClass {
        private int field1;
        private String field2;
        
        public void method1() {
            int localVar = 0;
            if (field1 > 0) {
                localVar = field1 * 2;
            }
        }
        
        public int method2(String param) {
            int result = 0;
            for (int i = 0; i < param.length(); i++) {
                result += param.charAt(i);
            }
            return result;
        }
    }
    """
    file_path = tmp_path / "TestClass.java"
    file_path.write_text(java_content)
    return str(file_path)


def test_base_analyzer_initialization(base_analyzer):
    """Test that BaseCKAnalyzer is initialized correctly."""
    assert base_analyzer is not None
    assert hasattr(base_analyzer, 'ck_jar_path')
    assert os.path.exists(base_analyzer.ck_jar_path)


def test_ck_metrics_analyzer_initialization(ck_metrics_analyzer):
    """Test that CKMetricsAnalyzer is initialized correctly."""
    assert ck_metrics_analyzer is not None
    assert hasattr(ck_metrics_analyzer, 'src_dir')
    assert hasattr(ck_metrics_analyzer, 'output_dir')
    assert os.path.exists(ck_metrics_analyzer.src_dir)
    assert os.path.exists(ck_metrics_analyzer.output_dir)


def test_solution_metrics_analyzer_initialization(solution_metrics_analyzer):
    """Test that SolutionMetricsAnalyzer is initialized correctly."""
    assert solution_metrics_analyzer is not None
    assert hasattr(solution_metrics_analyzer, 'ck_jar_path')
    assert os.path.exists(solution_metrics_analyzer.ck_jar_path)


def test_run_ck_metrics(base_analyzer, tmp_path):
    """Test running CK metrics on a directory."""
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    output_dir.mkdir()

    # Create a sample Java file in source directory
    java_file = source_dir / "TestClass.java"
    java_file.write_text("public class TestClass {}")

    with patch('subprocess.run') as mock_run:
        # Mock the subprocess output to return success
        mock_run.return_value = MagicMock(returncode=0)

        # Create a sample CSV file with exactly one entry
        csv_content = """file,cbo,wmc,dit,noc,rfc,lcom,ca,ce,npm,lcom3,loc,dam,moa,mfa,cam,ic,cbm,amc,avg_cc,max_cc,bug_severity,abstractMethodsQty,anonymousClassesQty,assignmentsQty
TestClass.java,2,3,1,0,4,0.5,1,1,2,0.6,20,0.8,2,0.5,0.7,0.4,1,0.3,2.5,4,MEDIUM,0,0,2"""

        csv_file = output_dir / "ck_outputclass.csv"
        csv_file.write_text(csv_content)

        # Mock the file move operation
        with patch('shutil.move') as mock_move:
            metrics = base_analyzer.run_ck_metrics(
                str(source_dir), str(output_dir))

            # Verify the command was constructed correctly
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "java" in args[0]
            assert "-jar" in args
            assert base_analyzer.ck_jar_path in args
            assert str(source_dir) in args
            assert str(output_dir) in args

            # Verify metrics were parsed correctly
            assert len(metrics) == 1
            assert metrics[0]['file'] == 'TestClass.java'
            assert metrics[0]['cbo'] == '2'
            assert metrics[0]['wmc'] == '3'
            assert metrics[0]['bug_severity'] == 'MEDIUM'
            assert metrics[0]['abstractMethodsQty'] == '0'
            assert metrics[0]['anonymousClassesQty'] == '0'
            assert metrics[0]['assignmentsQty'] == '2'


def test_parse_class_metrics(base_analyzer, tmp_path):
    """Test parsing class metrics from CSV file."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create a sample CSV file
    csv_content = """file,cbo,wmc,dit,noc,rfc,lcom,ca,ce,npm,lcom3,loc,dam,moa,mfa,cam,ic,cbm,amc,avg_cc,max_cc,bug_severity
TestClass.java,2,3,1,0,4,0.5,1,1,2,0.6,20,0.8,2,0.5,0.7,0.4,1,0.3,2.5,4,MEDIUM"""

    csv_file = output_dir / "ck_outputclass.csv"
    csv_file.write_text(csv_content)

    metrics = base_analyzer._parse_class_metrics(str(output_dir))

    assert len(metrics) == 1
    assert metrics[0]['file'] == 'TestClass.java'
    assert metrics[0]['cbo'] == '2'
    assert metrics[0]['wmc'] == '3'
    assert metrics[0]['bug_severity'] == 'MEDIUM'


def test_get_metrics_for_file(base_analyzer, tmp_path):
    """Test getting metrics for a specific file."""
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    output_dir.mkdir()

    # Create a sample Java file in source directory
    java_file = source_dir / "TestClass.java"
    java_file.write_text("public class TestClass {}")

    # Create a sample CSV file
    csv_content = """file,cbo,wmc,dit,noc,rfc,lcom,ca,ce,npm,lcom3,loc,dam,moa,mfa,cam,ic,cbm,amc,avg_cc,max_cc,bug_severity
TestClass.java,2,3,1,0,4,0.5,1,1,2,0.6,20,0.8,2,0.5,0.7,0.4,1,0.3,2.5,4,MEDIUM"""

    csv_file = output_dir / "ck_outputclass.csv"
    csv_file.write_text(csv_content)

    with patch('app.services.MetricAnalyzer.BaseCKAnalyzer.run_ck_metrics') as mock_run:
        mock_run.return_value = [
            {'file': 'TestClass.java', 'cbo': '2',
                'wmc': '3', 'bug_severity': 'MEDIUM'},
            {'file': 'OtherClass.java', 'cbo': '1',
                'wmc': '2', 'bug_severity': 'LOW'}
        ]

        metrics = base_analyzer.get_metrics_for_file(
            'TestClass.java', str(source_dir), str(output_dir))

        assert len(metrics) == 1
        assert metrics[0]['file'] == 'TestClass.java'
        assert metrics[0]['cbo'] == '2'
        assert metrics[0]['wmc'] == '3'
        assert metrics[0]['bug_severity'] == 'MEDIUM'


def test_get_metrics_for_file_no_match(base_analyzer, tmp_path):
    """Test getting metrics for a non-existent file."""
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    output_dir.mkdir()

    with patch('app.services.MetricAnalyzer.BaseCKAnalyzer.run_ck_metrics') as mock_run:
        mock_run.return_value = [
            {'file': 'TestClass.java', 'cbo': '2',
                'wmc': '3', 'bug_severity': 'MEDIUM'}
        ]

        metrics = base_analyzer.get_metrics_for_file(
            'NonExistent.java', str(source_dir), str(output_dir))
        assert len(metrics) == 0


