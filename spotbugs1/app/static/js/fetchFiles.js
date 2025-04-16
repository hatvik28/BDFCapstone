document.getElementById('repoForm').addEventListener('submit', function(event) {
    event.preventDefault();
    const repoUrl = document.getElementById('repo_url').value;

    const repoNameMatch = repoUrl.match(/github\.com\/([^/]+\/[^/]+)/);
    if (!repoNameMatch) {
        document.getElementById('results').innerHTML = `<p class="error">Invalid GitHub repository URL.</p>`;
        return;
    }
    const repoName = repoNameMatch[1];

    fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `repo_url=${encodeURIComponent(repoUrl)}`
    })
    .then(response => response.json())
    .then(data => {
        const resultsDiv = document.getElementById('results');
        const fileDropdown = document.getElementById('fileDropdown');
        resultsDiv.innerHTML = '';
        fileDropdown.innerHTML = '<option value="" disabled selected>Select a Java file</option>';

        if (data.error) {
            // Check if it's the cloned repo error
            if (data.error.includes("Failed to clear previous cloned repo folder")) {
                const alertBox = document.getElementById('buildAlertContainer');
                const alertMsg = document.getElementById('buildAlertMessage');
                alertMsg.innerHTML = "Unable to access repository folder. Please refresh the page and try again.";
                alertBox.style.display = 'block';
                return;
            }
            resultsDiv.innerHTML = `<p class="error">Error: ${data.error}</p>`;
            return;
        }

        fetch(`/files?repo_name=${repoName}`, { method: 'GET' })
        .then(response => response.json())
        .then(fileData => {
            if (fileData.files && fileData.files.length > 0) {
                fileData.files.forEach(file => {
                    const option = document.createElement('option');
                    option.value = file;
                    option.textContent = file;
                    fileDropdown.appendChild(option);
                });
            } else {
                resultsDiv.innerHTML = `<p>No Java files found in the repository.</p>`;
            }
        })
        .catch(error => {
            resultsDiv.innerHTML = `<p class="error">Error fetching Java files: ${error.message}</p>`;
        });
    })
    .catch(error => {
        document.getElementById('results').innerHTML = `<p class="error">Error: ${error.message}</p>`;
    });
});
