import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get sensitive credentials from environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
LLM_API_KEY = os.getenv("LLM_API_KEY")

# Configuration variables
SPOTBUGS_REPORT_PATH = "spotbugs_report.xml"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OUTPUT_DIR = os.path.join(BASE_DIR, '..', '..', 'cloned_repo')
BIN_DIR = os.path.join(BASE_DIR, '..', '..', 'bin')

REPO_ROOT_DIR = os.path.join(BASE_DIR, '..', '..', 'cloned_repo')

GOOGLE_FORMATTER_PATH = os.path.join(os.path.dirname(os.path.dirname(
    __file__)), 'tools', 'google-java-format-1.25.2-all-deps.jar')

# change path to your location
PMD_PATH = os.path.join(os.path.dirname(os.path.dirname(
    __file__)), 'tools', 'pmd-dist-7.7.0-bin', 'pmd-bin-7.7.0', 'bin', 'pmd.bat')

PMD_RULESET_PATH = "pmd-rules.xml"
PMD_REPORT_PATH = "pmd_report.xml"

SPOTBUGS_PATH = os.path.join(os.path.dirname(os.path.dirname(
    __file__)), 'tools', 'spotbugs-4.8.6', 'bin', 'spotbugs.bat')
