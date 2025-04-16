// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Handle Send to LLM button click
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('btn-llm')) {
            const spinner = document.getElementById("loadingSpinner");
            if (!spinner) {
                console.error("Loading spinner not found");
                return;
            }
            spinner.style.display = "flex"; 
            const bug = JSON.parse(decodeURIComponent(event.target.getAttribute('data-bug')));
            sendBugToLLM(bug);
        }
        
        // Handle Submit Feedback button click
        if (event.target.classList.contains('btn-submit-feedback')) {
            const solutionBox = event.target.closest('.solution-box');
            if (!solutionBox) {
                console.error("Could not find parent solution box");
                return;
            }

            const feedbackInput = solutionBox.querySelector('.feedback-input');
            if (!feedbackInput || !feedbackInput.value.trim()) {
                alert("Please provide feedback before submitting.");
                return;
            }

            const bug = JSON.parse(decodeURIComponent(solutionBox.querySelector('.apply-solution-btn').getAttribute('data-bug')));
            const solutionNumber = parseInt(solutionBox.dataset.solutionNumber);
            const originalCode = window.currentFileContent;
            const currentSolution = solutionBox.querySelector('.solution-code').textContent;

            // Disable the button and show loading state
            event.target.disabled = true;
            const originalText = event.target.textContent;
            event.target.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';

            fetch('/update_solution', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    bug_type: bug.type,
                    description: bug.description,
                    original_code: originalCode,
                    current_solution: currentSolution,
                    user_feedback: feedbackInput.value.trim(),
                    solution_number: solutionNumber,
                    filename: bug.file,
                    bug_line: bug.line
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(`Error updating solution: ${data.error}`);
                    return;
                }

                // Update the solution code display
                const solutionCode = solutionBox.querySelector('.solution-code');
                solutionCode.textContent = data.updated_solution;

                // Clear the feedback input
                feedbackInput.value = '';

                // Show success message
                alert('Solution updated successfully!');
            })
            .catch(error => {
                console.error('Error:', error);
                alert(`Failed to update solution: ${error.message}`);
            })
            .finally(() => {
                // Restore button state
                event.target.disabled = false;
                event.target.textContent = originalText;
            });
        }
    });
});

function sendBugToLLM(bug) {
    const selectedFile = document.getElementById('fileDropdown').value; // Get selected file name
    const spinner = document.getElementById("loadingSpinner");

    if (!selectedFile) {
        alert("Please select a file first.");
        if (spinner) spinner.style.display = "none";
        return;
    }

    // Use the stored original file content instead of trying to extract it from UI
    let fileContent = window.currentFileContent;
    
    // If for some reason we don't have the file content cached, fall back to fetching it
    if (!fileContent) {
        console.warn("Original file content not available in cache, fetching from server");
        spinner.style.display = "flex";
        
        fetch('/file_content', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: selectedFile })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(`Error fetching file content: ${data.error}`);
                if (spinner) spinner.style.display = "none";
                return;
            }
            
            fileContent = data.content.replace(/```[a-zA-Z]*\n?/g, "").trim();
            sendToLLMWithContent(bug, selectedFile, fileContent, spinner);
        })
        .catch(error => {
            alert(`Error retrieving file content: ${error}`);
            if (spinner) spinner.style.display = "none";
        });
    } else {
        sendToLLMWithContent(bug, selectedFile, fileContent, spinner);
    }
}

// Extract the actual LLM call to a separate function
function sendToLLMWithContent(bug, selectedFile, fileContent, spinner) {
    // Send bug an file content to the LLM
    fetch('/send_to_llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            bug: bug,
            file_name: selectedFile,
            file_content: fileContent
        })
    })
    .then(response => response.json())
    .then(data => {
        const solutionDisplay = document.getElementById('solutionDisplay');
        solutionDisplay.innerHTML = ""; // Clear previous results

        if (data.error) {
            solutionDisplay.innerHTML = `<p class="error">Error: ${data.error}</p>`;
            if (spinner) spinner.style.display = "none";
            return;
        }

        // Create and append header section
        const headerSection = createHeaderSection(bug);
        solutionDisplay.appendChild(headerSection);

        // Create and append each solution
        data.solutions.forEach((solution, index) => {
            const solutionElement = createSolutionElement(solution, index, bug);
            solutionDisplay.appendChild(solutionElement);
        });
    })
    .catch(error => {
        const solutionDisplay = document.getElementById('solutionDisplay');
        solutionDisplay.innerHTML = `<p class="error">Error: ${error}</p>`;
        if (spinner) spinner.style.display = "none"; 
    })
    .finally(() => {
        if (spinner) spinner.style.display = "none";
    });
}

// Helper function to create the header section
function createHeaderSection(bug) {
    const headerSection = document.createElement('div');
    headerSection.classList.add('header-section');

    const bugHeader = document.createElement('h4');
    bugHeader.textContent = "Solutions for Bugs";
    headerSection.appendChild(bugHeader);

    const bugDescription = document.createElement('p');
    bugDescription.innerHTML = `<strong>Bug Description:</strong> ${bug.description || "No description available."}`;
    headerSection.appendChild(bugDescription);

    return headerSection;
}

// Helper function to create a solution element
function createSolutionElement(solution, index, bug) {
    const solutionBox = document.createElement('div');
    solutionBox.classList.add('solution-box');
    solutionBox.dataset.solutionNumber = index + 1;  // Store solution number as a data attribute

    // Solution Header
    const solutionTitle = document.createElement('h5');
    solutionTitle.textContent = `Solution ${index + 1}`;
    solutionBox.appendChild(solutionTitle);

    // Buggy Code Section
    const buggyCodeSection = document.createElement('div');
    buggyCodeSection.classList.add('code-section');
    
    const buggyCodeLabel = document.createElement('p');
    buggyCodeLabel.classList.add('code-label');
    buggyCodeLabel.textContent = 'Original Code:';
    buggyCodeSection.appendChild(buggyCodeLabel);

    const buggyCode = document.createElement('pre');
    buggyCode.classList.add('buggy-code');
    buggyCode.textContent = bug.code_snippet;
    buggyCodeSection.appendChild(buggyCode);
    solutionBox.appendChild(buggyCodeSection);

    // Solution Code Section
    const solutionCodeSection = document.createElement('div');
    solutionCodeSection.classList.add('code-section');
    
    const solutionCodeLabel = document.createElement('p');
    solutionCodeLabel.classList.add('code-label');
    solutionCodeLabel.textContent = 'Fixed Code:';
    solutionCodeSection.appendChild(solutionCodeLabel);

    const solutionCode = document.createElement('pre');
    solutionCode.classList.add('solution-code');
    solutionCode.textContent = solution.solution;
    solutionCodeSection.appendChild(solutionCode);
    solutionBox.appendChild(solutionCodeSection);

    // Explanation
    const explanation = document.createElement('p');
    explanation.classList.add('solution-explanation');
    explanation.innerHTML = `<strong>Explanation:</strong> ${solution.explanation}`;
    solutionBox.appendChild(explanation);

    // Rating
    if (solution.rating) {
        const rating = document.createElement('p');
        rating.classList.add('solution-rating');
        rating.innerHTML = `<strong>Rating:</strong> ${solution.rating}/10`;
        solutionBox.appendChild(rating);
    }

    // Feedback Section
    const feedbackSection = document.createElement('div');
    feedbackSection.classList.add('feedback-section');
    
    const feedbackInput = document.createElement('textarea');
    feedbackInput.classList.add('feedback-input');
    feedbackInput.placeholder = 'Provide feedback on this solution...';
    feedbackSection.appendChild(feedbackInput);
    
    // Create button group
    const buttonGroup = document.createElement('div');
    buttonGroup.classList.add('button-group');
    
    // Submit Feedback button
    const feedbackButton = document.createElement('button');
    feedbackButton.classList.add('btn-feedback', 'btn-submit-feedback');
    feedbackButton.textContent = 'Submit Feedback';
    buttonGroup.appendChild(feedbackButton);

    // Calculate Metrics button
    const calcMetricsButton = document.createElement('button');
    calcMetricsButton.type = "button";
    calcMetricsButton.classList.add('btn-feedback', 'btn-calculate-metrics');
    calcMetricsButton.textContent = 'Calculate Metrics';
    calcMetricsButton.dataset.solutionNumber = index + 1;
    buttonGroup.appendChild(calcMetricsButton);

    // Apply Solution button
    const applyButton = createApplyButton(bug, solution, index + 1);
    applyButton.classList.add('btn-feedback', 'btn-apply-solution');
    buttonGroup.appendChild(applyButton);

    feedbackSection.appendChild(buttonGroup);
    solutionBox.appendChild(feedbackSection);

    // Metrics section
    const metricsSection = document.createElement('div');
    metricsSection.classList.add('metrics-section');
    metricsSection.id = `metrics-section-${index + 1}`;
    solutionBox.appendChild(metricsSection);

    // Add click event listener for Calculate Metrics
    calcMetricsButton.addEventListener('click', function() {
        calculateMetricsForSolution(selectedFilePath, index + 1, this);
    });

    return solutionBox;
}

// Function to calculate metrics for a solution on demand
function calculateMetricsForSolution(filename, solutionNumber, buttonElement) {
    // Show loading indicator
    const metricsSection = document.getElementById(`metrics-section-${solutionNumber}`);
    if (!metricsSection) return;
    
    // Disable the button and show loading
    if (buttonElement) {
        buttonElement.disabled = true;
        const originalText = buttonElement.textContent;
        buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Calculating...';
    }
    
    fetch('/calculate_metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            filename: filename,
            solution_number: solutionNumber
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            metricsSection.innerHTML = `<p class="text-danger">Error: ${data.error}</p>`;
        } else if (data.metrics) {
            // Create metrics HTML
            const metricsHTML = createMetricsHTML(data.metrics);
            metricsSection.innerHTML = metricsHTML;
        }
    })
    .catch(error => {
        metricsSection.innerHTML = `<p class="text-danger">Error calculating metrics: ${error}</p>`;
    })
    .finally(() => {
        // Re-enable the button and restore original text
        if (buttonElement) {
            buttonElement.disabled = false;
            buttonElement.textContent = 'Calculate Metrics';
        }
    });
}

// Helper function to create metrics HTML
function createMetricsHTML(metrics) {
    if (!metrics || !metrics.improvements) {
        return '<p>No metrics available</p>';
    }
    
    const improvements = metrics.improvements;
    
    let html = `
        <div class="metrics-summary mt-3 p-3" style="background-color: #2a2a40; border-radius: 8px;">
            <h4>Metrics Comparison</h4>
            <table class="table table-dark table-sm">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Before</th>
                        <th>After</th>
                        <th>Change</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    for (const [key, value] of Object.entries(improvements)) {
        const delta = value.delta;
        const arrow = delta < 0 ? '↓' : (delta > 0 ? '↑' : '→');
        const colorClass = delta < 0 ? 'text-success' : (delta > 0 ? 'text-danger' : 'text-muted');
        
        html += `
            <tr>
                <td>${key.toUpperCase()}</td>
                <td>${value.before}</td>
                <td>${value.after}</td>
                <td class="${colorClass}">${arrow} ${Math.abs(delta)}</td>
            </tr>
        `;
    }
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    return html;
}

// Helper function to create an apply button
function createApplyButton(bug, solution, solutionNumber) {
    const applyButton = document.createElement('button');
    applyButton.type = "button";
    applyButton.classList.add('apply-solution-btn');
    applyButton.textContent = "Apply Solution";
    
    // Set data attributes
    applyButton.setAttribute('data-filepath', bug.file_path || selectedFilePath);
    applyButton.setAttribute('data-solution', solution.solution);
    applyButton.setAttribute('data-code-snippet', bug.code_snippet);
    applyButton.setAttribute('data-solution-number', solutionNumber);
    applyButton.setAttribute('data-bug', encodeURIComponent(JSON.stringify(bug)));

    // Add click event listener
    applyButton.addEventListener('click', () => {
        applySolution(
            bug.file_path || selectedFilePath,
            bug.code_snippet,
            solution.solution,
            solutionNumber
        );
    });

    return applyButton;
}