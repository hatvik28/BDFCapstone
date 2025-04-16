import os
import subprocess
import re
import glob
import shutil
from typing import Tuple, List, Optional


class BuildSystemManager:
    def __init__(self, output_dir: str, bin_dir: str, spotbugs_path: str, repo_root_dir: str):
        """Initialize the BugAnalyzer with necessary paths."""
        # Convert all paths to absolute paths
        self.output_dir = os.path.abspath(output_dir)
        self.bin_dir = os.path.abspath(bin_dir)
        self.spotbugs_path = os.path.abspath(spotbugs_path)
        self.repo_root_dir = os.path.abspath(repo_root_dir)

    """Handles build system detection and operations."""

    def _detect_build_tool(self, project_dir: str) -> str:
        """Detect if the project uses Maven or Gradle."""
        project_dir = os.path.abspath(project_dir)
        if os.path.exists(os.path.join(project_dir, 'pom.xml')):
            return 'maven'
        elif os.path.exists(os.path.join(project_dir, 'build.gradle')):
            return 'gradle'
        return 'none'

    def _compile_maven_project(self, project_dir: str) -> bool:
        """Compile a Maven project and copy classes from target directories."""
        try:
            project_dir = os.path.abspath(project_dir)
            print(f"Starting Maven project compilation in {project_dir}")

            # Use Maven wrapper if available, otherwise fall back to global mvn
            wrapper_name = 'mvnw.bat' if os.name == 'nt' else './mvnw'
            wrapper_path = os.path.join(project_dir, wrapper_name)

            if os.path.exists(wrapper_path):
                cmd = [wrapper_name, 'clean', 'compile', '-DskipTests']
                print(
                    f"Found Maven wrapper at {wrapper_path}, using it for compilation")
            else:
                print("Maven wrapper not found, falling back to system's Maven command")
                cmd = ['mvn', 'clean', 'compile', '-DskipTests']

            print(f"Running Maven command: {' '.join(cmd)}")
            print(f"Working directory: {project_dir}")

            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                shell=(os.name == 'nt')
            )

            if result.returncode != 0:
                print(f"Maven compilation failed with error: {result.stderr}")
                return False

            # Find all target/classes directories
            class_dirs = []
            for root, dirs, _ in os.walk(project_dir):
                if 'target' in dirs:
                    target_dir = os.path.join(root, 'target', 'classes')
                    if os.path.exists(target_dir):
                        class_dirs.append(target_dir)

            if not class_dirs:
                print(
                    f"No target/classes directories found in {project_dir} - compilation might have failed")
                return False

            # Copy classes from all found directories
            for target_dir in class_dirs:
                print(f"Copying compiled classes from {target_dir}")
                self._copy_compiled_classes(target_dir)

            return True

        except Exception as e:
            print(f"Error during Maven project compilation: {str(e)}")
            return False

    def _compile_gradle_project(self, project_dir: str) -> bool:
        """Compile a Gradle project."""
        try:
            project_dir = os.path.abspath(project_dir)
            print(f"Starting Gradle project compilation in {project_dir}")

            # Get required Java version from build.gradle
            required_version = self._get_required_java_version(project_dir)
            print(f"Project requires Java version: {required_version}")

            # Use only the wrapper name because cwd is set
            wrapper_name = 'gradlew.bat' if os.name == 'nt' else './gradlew'
            wrapper_path = os.path.join(project_dir, wrapper_name)

            if os.path.exists(wrapper_path):
                # Try to find compatible Java version
                java_home = self._find_compatible_java(required_version)
                if java_home:
                    print(f"Using Java installation found at: {java_home}")
                    env = os.environ.copy()
                    env['JAVA_HOME'] = java_home
                    # Use only common JVM arguments
                    cmd = [wrapper_name, 'clean', 'compileJava', '-x', 'test',
                           '-Dorg.gradle.java.home=' + java_home,
                           '-Dorg.gradle.jvmargs=-Xmx2048m']
                else:
                    print(
                        "No compatible Java version found. Attempting to use system default Java")
                    cmd = [wrapper_name, 'clean', 'compileJava', '-x', 'test']
            else:
                print(
                    "Gradle wrapper not found. Trying to use system's Gradle installation")
                cmd = ['gradle', 'compileJava', '-x', 'test']

            print(f"Running Gradle command: {' '.join(cmd)}")
            print(f"Working directory: {project_dir}")

            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                shell=(os.name == 'nt'),
                env=env if 'env' in locals() else None
            )

            if result.returncode != 0:
                error_msg = f"Gradle compilation failed with error: {result.stderr}"
                print(error_msg)
                raise RuntimeError(error_msg)

            # Find the build/classes directory
            build_dir = os.path.join(
                project_dir, 'build', 'classes', 'java', 'main')
            if not os.path.exists(build_dir):
                print(
                    f"Gradle build directory not found at expected location: {build_dir}")
                return False

            # Copy compiled classes to our bin directory
            self._copy_compiled_classes(build_dir)
            return True

        except Exception as e:
            print(f"Error during Gradle project compilation: {str(e)}")
            return False

    def _get_required_java_version(self, project_dir: str) -> str:
        """Read the required Java version from build.gradle."""
        try:
            build_gradle = os.path.join(project_dir, 'build.gradle')
            if not os.path.exists(build_gradle):
                return None

            with open(build_gradle, 'r') as f:
                content = f.read()

            # Look for sourceCompatibility and targetCompatibility
            source_match = re.search(
                r'sourceCompatibility\s*=\s*[\'"]([^\'"]+)[\'"]', content)
            target_match = re.search(
                r'targetCompatibility\s*=\s*[\'"]([^\'"]+)[\'"]', content)

            if source_match:
                return source_match.group(1)
            elif target_match:
                return target_match.group(1)
            else:
                # Default to Java 8 if no version specified
                return '1.8'

        except Exception as e:
            print(
                f"Could not determine Java version from build.gradle: {str(e)}")
            return '1.8'  # Default to Java 8

    def _find_compatible_java(self, required_version: str) -> str:
        """Find a compatible Java version in the system, prioritizing Java 8."""
        try:
            # First try JAVA_HOME environment variable
            if 'JAVA_HOME' in os.environ:
                java_home = os.environ['JAVA_HOME']
                if os.path.exists(java_home):
                    print(
                        f"Using Java from JAVA_HOME environment variable: {java_home}")
                    return java_home

            # Prioritize Java 8 paths first
            java8_paths = [
                r"C:\Program Files\Java\jdk1.8.0_*",
                r"C:\Program Files (x86)\Java\jdk1.8.0_*"
            ]

            print("Looking for Java 8 installation first...")
            for base_path in java8_paths:
                # Try exact path first
                if os.path.exists(base_path):
                    print(f"Found Java 8 at: {base_path}")
                    return base_path

                # Try glob pattern for versioned paths
                matches = glob.glob(base_path)
                if matches:
                    # Sort matches to get the latest version
                    matches.sort(reverse=True)
                    print(f"Found Java 8 at: {matches[0]}")
                    return matches[0]

            # If Java 8 not found, try other versions
            other_versions = {
                '11': [
                    r"C:\Program Files\Java\jdk-11",
                    r"C:\Program Files (x86)\Java\jdk-11"
                ],
                '17': [
                    r"C:\Program Files\Java\jdk-17",
                    r"C:\Program Files (x86)\Java\jdk-17"
                ]
            }

            print("Java 8 not found, checking for Java 11 or 17 instead...")
            for version, paths in other_versions.items():
                for base_path in paths:
                    if os.path.exists(base_path):
                        print(f"Found Java {version} at: {base_path}")
                        return base_path
                    matches = glob.glob(base_path)
                    if matches:
                        matches.sort(reverse=True)
                        print(f"Found Java {version} at: {matches[0]}")
                        return matches[0]

            # Try to find Java in PATH
            try:
                result = subprocess.run(
                    ['where', 'java'], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout:
                    java_path = result.stdout.strip().split('\n')[0]
                    java_dir = os.path.dirname(java_path)
                    if os.path.exists(java_dir):
                        print(f"Found Java in system PATH: {java_dir}")
                        return java_dir
            except Exception as e:
                print(f"Could not locate Java in system PATH: {str(e)}")

            print("Could not find any compatible Java installation")
            return None

        except Exception as e:
            print(f"Error while searching for compatible Java: {str(e)}")
            return None

    def _copy_compiled_classes(self, source_dir: str):
        """Copy compiled classes to our bin directory."""
        try:
            # Clear existing classes
            for file in os.listdir(self.bin_dir):
                if file.endswith('.class'):
                    os.remove(os.path.join(self.bin_dir, file))

            # Copy new classes
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.endswith('.class'):
                        src_path = os.path.join(root, file)
                        rel_path = os.path.relpath(src_path, source_dir)
                        dst_path = os.path.join(self.bin_dir, rel_path)
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        shutil.copy2(src_path, dst_path)

            print(
                f"Successfully copied all compiled class files to {self.bin_dir}")

        except Exception as e:
            print(f"Error while copying compiled classes: {str(e)}")

    def _find_build_files(self, start_dir: str) -> Tuple[str, str]:
        """Find build files (pom.xml, build.gradle) in the directory and its subdirectories."""
        try:
            # First check the root directory
            root_pom = os.path.join(start_dir, 'pom.xml')
            root_gradle = os.path.join(start_dir, 'build.gradle')
            root_gradle_kts = os.path.join(start_dir, 'build.gradle.kts')

            if os.path.exists(root_pom):
                return start_dir, 'maven'
            if os.path.exists(root_gradle) or os.path.exists(root_gradle_kts):
                return start_dir, 'gradle'

            # If not found in root, search in subdirectories
            for root, _, files in os.walk(start_dir):
                # Skip .git directory
                if '.git' in root:
                    continue

                pom_path = os.path.join(root, 'pom.xml')
                gradle_path = os.path.join(root, 'build.gradle')
                gradle_kts_path = os.path.join(root, 'build.gradle.kts')

                if os.path.exists(pom_path):
                    print(f"Found Maven's pom.xml in subdirectory: {root}")
                    return root, 'maven'
                if os.path.exists(gradle_path) or os.path.exists(gradle_kts_path):
                    print(f"Found Gradle's build file in subdirectory: {root}")
                    return root, 'gradle'

            return None, None

        except Exception as e:
            print(f"Error while searching for build files: {str(e)}")
            return None, None

    def _find_project_root(self, file_path: str) -> str:
        """Find the project root directory by looking for build files in parent directories.

        This is a fallback method when _find_build_files doesn't find build files in the repository.
        It looks up the directory tree for build files (pom.xml or build.gradle).

        Args:
            file_path: Path to the Java file being analyzed

        Returns:
            Path to the project root directory, or None if not found
        """
        current_dir = os.path.dirname(file_path)

        # Look up to 5 levels up for build files
        for _ in range(5):
            if os.path.exists(os.path.join(current_dir, 'pom.xml')) or \
               os.path.exists(os.path.join(current_dir, 'build.gradle')):
                print(f"Found build file in parent directory: {current_dir}")
                return current_dir

            # Move up one directory
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:  # We've reached the root
                break
            current_dir = parent_dir

        print("No build files found in any parent directories")
        return None

    def compile_java_files(self, file_path: str, bin_dir: str) -> bool:
        """Compile Java files with proper classpath handling and dependency resolution."""
        try:
            print(f"Starting compilation process for {file_path}")

            # Check if the file exists
            if not os.path.exists(file_path):
                print(
                    f"Cannot compile - source file does not exist: {file_path}")
                return False

            # Use REPO_ROOT_DIR for build tool detection
            print(f"Checking repository root directory: {self.repo_root_dir}")

            # Search for build files in root and subdirectories
            project_dir, build_tool = self._find_build_files(
                self.repo_root_dir)

            if not project_dir:
                print("No build tool found in repository root or subdirectories")
                # Fallback to searching up from file directory
                project_dir = self._find_project_root(file_path)
                if project_dir:
                    build_tool = self._detect_build_tool(project_dir)

            if not project_dir:
                print("Could not locate a project root with build configuration")
                # Fallback to file's directory
                project_dir = os.path.dirname(file_path)
                build_tool = 'none'

            print(f"Build tool detected: {build_tool}")
            print(f"Project root directory: {project_dir}")

            if build_tool == 'maven':
                if not self._compile_maven_project(project_dir):
                    return False
            elif build_tool == 'gradle':
                try:
                    if not self._compile_gradle_project(project_dir):
                        return False
                except RuntimeError as e:
                    raise e
            else:
                print("No build tool detected, falling back to direct javac compilation")
                if not self._compile_with_javac(file_path, bin_dir):
                    return False

            # Check for compiled classes using self.bin_dir consistently
            compiled_classes = []
            for root, _, files in os.walk(self.bin_dir):
                for file in files:
                    if file.endswith('.class'):
                        compiled_classes.append(os.path.join(root, file))

            if not compiled_classes:
                print(
                    f"Compilation failed - no class files were found in {self.bin_dir}")
                return False

            print(
                f"Compilation successful. Found {len(compiled_classes)} class files")
            return True
        except Exception as e:
            print(f"Error during compilation: {str(e)}")
            return False

    def _compile_with_javac(self, file_path: str, bin_dir: str) -> bool:
        """Compile Java files directly using javac."""
        try:
            file_path = os.path.abspath(file_path)
            bin_dir = os.path.abspath(bin_dir)
            print(f"Compiling Java file directly with javac: {file_path}")

            # Get the directory containing the target file
            target_dir = os.path.dirname(file_path)
            print(f"Source directory: {target_dir}")

            # Find all dependent files
            dependent_files = self._find_dependent_files(file_path)
            print(
                f"Found {len(dependent_files)} dependent Java files to include in compilation")

            # Combine target file with its dependencies
            java_files = [file_path] + dependent_files
            print(f"Total files to compile: {len(java_files)}")

            # Create classpath including:
            # 1. Output directory (where source files are)
            # 2. Binary directory (where compiled classes will be)
            classpath = [
                self.output_dir,
                bin_dir
            ]

            # Add any external dependencies if specified
            if hasattr(self, 'external_deps') and self.external_deps:
                classpath.extend(self.external_deps)

            # Construct the compilation command
            cmd = [
                "javac",
                "-d", bin_dir,
                "-cp", os.pathsep.join(classpath),
                "-encoding", "UTF-8",
                "-Xlint:none",  # Disable warnings
                "-Xlint:unchecked",  # Enable unchecked warnings
                "-Xlint:deprecation",  # Enable deprecation warnings
                "-sourcepath", self.output_dir  # Add sourcepath to help find dependencies
            ]

            # Add all files to compile
            cmd.extend(java_files)

            print(f"Running javac command: {' '.join(cmd)}")

            # Run the compilation
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on non-zero exit
            )

            # Check compilation result
            if result.returncode != 0:
                print(
                    f"Javac compilation failed with return code {result.returncode}")
                print(f"Compiler error output:\n{result.stderr}")
                return False

            # Verify that .class files were created
            class_files = [f for f in os.listdir(
                bin_dir) if f.endswith(".class")]
            if not class_files:
                print(
                    f"Javac compilation completed but no class files were created in {bin_dir}")
                print(f"Contents of {bin_dir}: {os.listdir(bin_dir)}")
                return False

            print(
                f"Javac compilation successful. Created {len(class_files)} class files")
            return True

        except Exception as e:
            print(f"Error during javac compilation: {str(e)}")
            return False

    def _find_dependent_files(self, file_path: str) -> List[str]:
        """Find all Java files that the target file depends on."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all import statements
            import_pattern = r'import\s+([^;]+);'
            imports = re.findall(import_pattern, content)
            print(f"Found {len(imports)} imports in {file_path}")

            # Get the package name of the target file
            package_pattern = r'package\s+([^;]+);'
            package_match = re.search(package_pattern, content)
            target_package = package_match.group(1) if package_match else ""
            print(f"Source file package: {target_package}")

            # Find all Java files in the project
            all_java_files = []
            for root, _, files in os.walk(self.output_dir):
                for file in files:
                    if file.endswith('.java'):
                        all_java_files.append(os.path.join(root, file))

            # Find files that contain the imported classes
            dependent_files = []
            for java_file in all_java_files:
                if java_file == file_path:
                    continue

                with open(java_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()

                # Get the package of this file
                file_package_match = re.search(package_pattern, file_content)
                file_package = file_package_match.group(
                    1) if file_package_match else ""
                print(
                    f"Checking dependency: {os.path.basename(java_file)} in package {file_package}")

                # Check if this file contains any of the imported classes
                for imp in imports:
                    # Convert import to class name
                    class_name = imp.split('.')[-1]
                    # Look for class declaration
                    if f"class {class_name}" in file_content:
                        print(
                            f"Found dependency: {os.path.basename(java_file)} contains imported class {class_name}")
                        dependent_files.append(java_file)
                        break

                # If files are in the same package, check for direct references
                if file_package == target_package:
                    # Look for class declarations that are referenced in the target file
                    class_decl_pattern = r'class\s+(\w+)'
                    class_decls = re.findall(class_decl_pattern, file_content)
                    for decl in class_decls:
                        if decl in content:
                            print(
                                f"Found same-package dependency: {os.path.basename(java_file)} contains class {decl}")
                            dependent_files.append(java_file)
                            break

            return list(set(dependent_files))  # Remove duplicates

        except Exception as e:
            print(f"Error while finding dependencies: {str(e)}")
            return []
