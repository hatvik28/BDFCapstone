BDF Capstone - Java Bug Detection & Fixing Tool


An AI-powered tool for detecting, analyzing, and automatically fixing bugs in Java code**

## Overview

BDF Capstone is a web-based application that leverages static analysis tools and Large Language Models (LLMs) to detect bugs in Java code and generate intelligent fixes. The tool integrates with GitHub repositories, allowing seamless analysis, fixing, and committing of code changes.

## Features

- **Dual Analysis Engines**

  - **SpotBugs**: Bytecode-level analysis for detecting runtime bugs
  - **PMD**: Static source code analysis for code quality issues

- **AI-Powered Bug Fixing**

  - Generates multiple solution alternatives using OpenAI/Claude
  - User feedback integration for solution refinement
  - Code formatting with Google Java Format

- **CK Metrics Analysis**

  - Tracks code quality metrics before and after fixes
  - Measures WMC (Weighted Method Count), LOC (Lines of Code), and more
  - Visualizes metric improvements

- **GitHub Integration**

  - Clone and analyze any public/private repository
  - Commit and push fixes directly to GitHub
  - Fork support with upstream remote configuration

- **Modern Web Interface**
  - Real-time bug detection results
  - Side-by-side code comparison (original vs. fixed)
  - Interactive solution selection and validation

## Prerequisites

- **Python 3.8+**
- **Java JDK 8+** (for SpotBugs bytecode analysis)
- **Git** (for repository cloning)
- **API Keys**: OpenAI and/or Anthropic Claude API key

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/BDFCapstone.git
cd BDFCapstone
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```env
GITHUB_TOKEN=your_github_personal_access_token
OPENAI_API_KEY=your_openai_api_key
CLAUDE_API_KEY=your_anthropic_api_key
```

### 5. Run the Application

```bash
python run.py
```

The application will be available at `http://localhost:5000`

## Usage

### Step 1: Analyze a Repository

1. Enter a GitHub repository URL in the input field
2. Click **Fetch** to clone and load Java files

### Step 2: Select Analysis Tool

Choose between:

- **SpotBugs** - For bytecode analysis (detects null pointer dereferences, resource leaks, etc.)
- **PMD** - For static code analysis (detects code smells, unused variables, etc.)

### Step 3: View and Fix Bugs

1. Select a Java file from the dropdown
2. Click **View File** to analyze
3. Review detected bugs in the "Bugs Detected" panel
4. Click **Send to LLM** to generate AI-powered solutions

### Step 4: Apply and Validate

1. Review the generated solutions
2. Click **Calculate Metrics** to compare before/after metrics
3. Click **Apply Solution** to apply the fix
4. Click **Validate** to verify the bug is fixed
5. Click **Commit Changes to GitHub** to push the fix


## Supported Bug Types

### SpotBugs Categories

- Null Pointer Dereferences
- Resource Leaks
- Infinite Loops
- Dead Stores
- Synchronization Issues
- Security Vulnerabilities

### PMD Categories

- Unused Variables
- Empty Catch Blocks
- Unnecessary Object Creation
- Code Style Violations
- Best Practice Violations


## Acknowledgments

- [SpotBugs](https://spotbugs.github.io/) - Static analysis tool for Java
- [PMD](https://pmd.github.io/) - Source code analyzer
- [CK Metrics](https://github.com/mauricioaniche/ck) - Code metrics calculator
- [Google Java Format](https://github.com/google/google-java-format) - Code formatter

**Built for Penn State CapStone**

</div>
