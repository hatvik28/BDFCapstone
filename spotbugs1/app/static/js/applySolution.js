function applySolution(filePath, codeSnippet, solution, solutionNumber) {
    // Show a loading indicator for the metrics
    const fixedCodePreview = document.getElementById("fixedCodePreview");
    if (fixedCodePreview) {
        fixedCodePreview.innerHTML = '<div class="text-center mt-3"><i class="fas fa-spinner fa-spin"></i> Applying solution and calculating metrics...</div>';
    }
    
    fetch("/apply_solution", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            file_path: filePath, 
            code_snippet: codeSnippet, 
            solution: solution,
            solution_number: solutionNumber
        }),
    })
    .then((response) => response.json())
    .then((data) => {
        const solutionDisplay = document.getElementById("solutionDisplay");
        const fixedCodePreview = document.getElementById("fixedCodePreview");

        if (data.error) {
            console.error("Error response:", data.error);
            solutionDisplay.innerHTML = `<p class="error">Error: ${data.error}</p>`;
            if (fixedCodePreview) {
                fixedCodePreview.innerHTML = '<p class="error">Failed to apply solution</p>';
            }
        } else {
            console.log("Solution applied successfully!");
            solutionDisplay.innerHTML = `<p class="success">${data.message}</p>`;

            // Use full_solution if available, otherwise fall back to corrected_code
            let cleanedFixedCode = (data.full_solution || data.corrected_code).replace(/```[a-zA-Z]*\n?/g, "").trim();
            const lines = cleanedFixedCode.split(/\r?\n/); 

            let lineNumbersHTML = '';
            let codeLinesHTML = '';

            lines.forEach((line, index) => {
                // Preserve blank lines by using &nbsp;
                const safeLine = line === "" ? "&nbsp;" : line.replace(/</g, "&lt;").replace(/>/g, "&gt;");

                // Add line numbers
                lineNumbersHTML += `<div>${index + 1}</div>`;

                // Add properly formatted code
                codeLinesHTML += `<div>${safeLine}</div>`;
            });

            // Create the metrics HTML
            let metricsHTML = '';
            if (data.metrics && !data.metrics.error) {
                metricsHTML = createMetricsHTML(data.metrics);
            }

            fixedCodePreview.innerHTML = `
                <div id="fixedCodeContainer" style="display: flex; border: 1px solid #ddd; background-color: #f5f5f5; 
                        max-height: 400px; overflow-y: auto; font-family: monospace; white-space: pre;">
                    <div id="fixedLineNumbers" style="text-align: right; padding: 10px; color: #999; 
                            border-right: 2px solid #ddd; min-width: 50px;">
                        ${lineNumbersHTML}
                    </div>
                    <div id="fixedCodeLines" style="padding: 10px; flex-grow: 1;">
                        ${codeLinesHTML}
                    </div>
                </div>
                ${metricsHTML}
            `;

            const fixedCodeContainer = document.getElementById("fixedCodeContainer");
            const fixedLineNumbers = document.getElementById("fixedLineNumbers");

            if (fixedCodeContainer && fixedLineNumbers) {
                fixedCodeContainer.addEventListener("scroll", function() {
                    fixedLineNumbers.scrollTop = fixedCodeContainer.scrollTop; // Sync vertical scrolling
                });
            }
        }
    })
    .catch((error) => {
        console.error("Fetch error:", error);
        const solutionDisplay = document.getElementById("solutionDisplay");
        solutionDisplay.innerHTML = `<p class="error">Error: ${error}</p>`;
        const fixedCodePreview = document.getElementById("fixedCodePreview");
        if (fixedCodePreview) {
            fixedCodePreview.innerHTML = '<p class="error">Failed to apply solution</p>';
        }
    });
}

// Helper function to create metrics HTML
function createMetricsHTML(metrics) {
    if (!metrics || !metrics.improvements) {
        return '';
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

let selectedFilePath = ""; // Global variable to store the selected file

document.getElementById("fileDropdown").addEventListener("change", function(event) {
    selectedFilePath = event.target.value; // Store the selected file path
    console.log("Selected file updated:", selectedFilePath);
});

document.addEventListener("click", function (event) {
    if (event.target && event.target.matches(".apply-solution-btn")) {
        const solutionBox = event.target.closest(".solution-box");
        if (!solutionBox) return;

        // Always get the most recent solution code from the UI
        const currentSolution = solutionBox.querySelector(".solution-code").innerText.trim();
        
        // For the code to replace, use the buggy-code if it exists,
        // otherwise look for the original snippet in the fixedCodePreview
        let codeToReplace = "";
        if (solutionBox.querySelector(".buggy-code")) {
            // If this is the first application, use the original buggy code
            codeToReplace = solutionBox.querySelector(".buggy-code").innerText.trim();
        } else {
            // After feedback, check if we have a special data attribute that holds the current solution in the repo
            const currentRepoCode = solutionBox.getAttribute("data-current-repo-code");
            if (currentRepoCode) {
                console.log("[DEBUG] Using tracked repo code as the code to replace");
                codeToReplace = currentRepoCode;
            }
            // If no tracked repo code, try to get from fixedCodePreview
            else {
                const fixedCodePreview = document.getElementById("fixedCodePreview");
                if (fixedCodePreview && fixedCodePreview.textContent.trim()) {
                    console.log("[DEBUG] Using current code from fixedCodePreview");
                    codeToReplace = fixedCodePreview.textContent.trim();
                } else {
                    // As a last resort, use previous solution
                    const previousSolution = solutionBox.getAttribute("data-previous-solution");
                    if (previousSolution) {
                        console.log("[DEBUG] Using previous solution as code to replace");
                        codeToReplace = previousSolution;
                    } else {
                        // Complete fallback
                        console.log("[DEBUG] Complete fallback: Using current solution as the code to replace");
                        codeToReplace = currentSolution;
                    }
                }
            }
        }

        // Store the current solution as the previous solution for future reference
        solutionBox.setAttribute("data-previous-solution", currentSolution);

        console.log("[DEBUG] Code to replace length:", codeToReplace.length);
        console.log("[DEBUG] Current solution length:", currentSolution.length);
        
        const solutionNumber = parseInt(event.target.getAttribute("data-solution-number")) || 1;

        let filePath = event.target.getAttribute("data-filepath");

        if (!filePath) {
            console.error("File path is missing! Using selectedFilePath instead.");
            filePath = selectedFilePath;  // Use the selected file if no path is available
        }
        
        if (!filePath.includes("/") && selectedFilePath) {
            // It's just a filename, use selected file path
            filePath = selectedFilePath;
        } else if (!filePath.startsWith("cloned_repo/")) {
            filePath = `cloned_repo/${filePath}`;
        }
        
        const correctedFilePath = filePath.startsWith("cloned_repo/") ? filePath : `cloned_repo/${filePath}`;

        applySolution(correctedFilePath, codeToReplace, currentSolution, solutionNumber);
    }
});
