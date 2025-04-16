window.currentFileContent = null; // Store the raw file content globally

function handleJavaVersionWarning(error) {
    const warningMessage = document.getElementById('warningMessage');
    const warningText = document.getElementById('warningText');
    const warningRecommendations = document.getElementById('warningRecommendations');

    const err = error.toLowerCase();
    const javaMismatch = err.includes('java version') ||
                         err.includes('unsupported class file') ||
                         err.includes('could not determine java version') ||
                         err.includes('no compatible java');

    if (javaMismatch) {
        warningText.textContent = 'Java version compatibility issue detected:';
        warningRecommendations.innerHTML = `
            <li>Install Java 8 or Java 17 (recommended)</li>
            <li>Set JAVA_HOME environment variable correctly</li>
            <li>Ensure Gradle/Maven project specifies supported Java version</li>
        `;
        warningMessage.style.display = 'block';
        return true;
    }

    return false;
}



document.getElementById('viewFileBtn').addEventListener('click', function () {
    const fileDropdown = document.getElementById('fileDropdown');
    const toolDropdown = document.getElementById('toolDropdown');
    const selectedFile = fileDropdown.value;
    const selectedTool = toolDropdown.value;

    if (!selectedFile) {
        alert('Please select a file.');
        return;
    }
    const spinner = document.getElementById("viewFileSpinner");
    spinner.style.display = "flex"; // show spinner

    console.log(`Selected file: ${selectedFile}, Tool: ${selectedTool}`);

    fetch('/file_content', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            filename: selectedFile,
            tool: selectedTool
        })
    })
        .then(response => response.json())
        .then(data => {
            const codePreviewDiv = document.getElementById('codePreview');
            const resultsDiv = document.getElementById('results');
            const warningMessage = document.getElementById('warningMessage');


            codePreviewDiv.innerHTML = '';
            resultsDiv.innerHTML = '';
            warningMessage.style.display = 'none';


            if (!data.success) {
                console.error("Build or analysis failed:", data.error);


                if (handleJavaVersionWarning(data.error)) {
                    spinner.style.display = "none";
                    return;
                }

                // Show Bootstrap alert with error message
                const alertBox = document.getElementById('buildAlertContainer');
                const alertMsg = document.getElementById('buildAlertMessage');

                alertMsg.textContent = data.error;
                alertBox.style.display = 'block';

                spinner.style.display = "none";
                return;

            }

            // Store the raw file content in a global variable
            window.currentFileContent = data.content.replace(/```[a-zA-Z]*\n?/g, "").trim();

            let cleanedCode = window.currentFileContent;
            const lines = cleanedCode.split(/\r?\n/);

            let lineNumbersHTML = '';
            let codeLinesHTML = '';

            lines.forEach((line, index) => {
                const safeLine = line === "" ? "&nbsp;" : line.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                lineNumbersHTML += `<div>${index + 1}</div>`;
                codeLinesHTML += `<div>${safeLine}</div>`;
            });

            codePreviewDiv.innerHTML = `
                <h3>${data.filename}</h3>
                <div id="codeContainer" style="display: flex; border: 1px solid #ddd; background-color: #f5f5f5; 
                            max-height: 400px; overflow-y: auto; font-family: monospace; white-space: pre;">
                    <div id="lineNumbers" style="text-align: right; padding: 10px; color: #999; 
                            border-right: 2px solid #ddd; min-width: 50px;">
                        ${lineNumbersHTML}
                    </div>
                    <div id="codeLines" style="padding: 10px; flex-grow: 1;">
                        ${codeLinesHTML}
                    </div>
                </div>
            `;

            resultsDiv.innerHTML = `<h2>Bugs Detected: ${data.num_bugs}</h2>`;

            if (data.analysis_tool) {
                resultsDiv.innerHTML += `<p><strong>Analysis Tool:</strong> ${data.analysis_tool}</p>`;
            }

            if (data.bugs && data.bugs.length > 0) {
                data.bugs.sort((a, b) => a.line - b.line);
                data.bugs.forEach(bug => {
                    resultsDiv.innerHTML += `
                        <div class="bug">
                            <p><strong>File:</strong> ${bug.file}</p>
                            <p><strong>Line:</strong> ${bug.line}</p>
                            <p><strong>Category:</strong> ${bug.category}</p>
                            <p><strong>Severity:</strong> ${bug.severity}</p>
                            <p><strong>Description:</strong> ${bug.description}</p>
                            <p><strong>Code Snippet:</strong><pre>${bug.code_snippet}</pre></p>
                            <button class="btn-llm" data-bug="${encodeURIComponent(JSON.stringify(bug))}">Send to LLM</button>
                            <button class="btn-validate" data-file="${data.filename}" data-line="${bug.line}" data-type="${bug.type}" data-tool="${data.analysis_tool.toLowerCase()}">Validate</button>
                        </div><hr>
                    `;
                });
            } else {
                resultsDiv.innerHTML += `<p>No bugs detected for this file.</p>`;
            }

            const metricsDiv = document.getElementById('metricsDisplay');
            metricsDiv.innerHTML = '';

            if (data.metrics && data.metrics.length > 0) {
                const selectedMetrics = ["class", "wmc", "loc", "fanin", "fanout", "returnQty", "loopQty", "comparisonsQty", "tryCatchQty", "variablesQty"];


                const metricsTable = document.createElement('table');
                metricsTable.style.width = "100%";
                metricsTable.style.borderCollapse = "collapse";
                metricsTable.style.fontSize = "12px";
                metricsTable.style.backgroundColor = "#2a2a40";

                const tbody = document.createElement('tbody');
                const metricRow = data.metrics[0];

                selectedMetrics.forEach(key => {
                    if (metricRow[key] !== undefined) {
                        const tr = document.createElement('tr');

                        const th = document.createElement('th');
                        th.textContent = key.toUpperCase();
                        th.style.border = "1px solid #555";
                        th.style.padding = "4px";
                        th.style.backgroundColor = "#444";
                        th.style.color = "#fff";
                        tr.appendChild(th);

                        const td = document.createElement('td');
                        td.textContent = metricRow[key];
                        td.style.border = "1px solid #555";
                        td.style.padding = "4px";
                        td.style.color = "#ddd";
                        tr.appendChild(td);

                        tbody.appendChild(tr);
                    }
                });

                metricsTable.appendChild(tbody);
                metricsDiv.innerHTML = `<h4 class="mt-3">CK Metrics</h4>`;
                metricsDiv.appendChild(metricsTable);
            } else {
                metricsDiv.innerHTML = "<p>No CK metrics available for this file.</p>";
            }

            spinner.style.display = "none";
        })
        .catch(error => {
            document.getElementById('results').innerHTML = `<p class="error">Error: ${error}</p>`;
            spinner.style.display = "none";
        });
});
