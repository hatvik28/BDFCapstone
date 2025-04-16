document.addEventListener('click', async function(event) {
    if (event.target.classList.contains('btn-validate')) {
        const filename = event.target.getAttribute('data-file');
        const bugLine = event.target.getAttribute('data-line');
        const bugType = event.target.getAttribute('data-type');
        const tool = event.target.getAttribute('data-tool') || 'spotbugs'; // Get the tool type, default to spotbugs
        const bugElement = event.target.closest('.bug');
        const bugsCountElement = document.querySelector("#results h2");

        // Get the original and patched code from the correct <pre> elements
        let originalCodeElement = document.querySelector("#codePreview");
        let patchedCodeElement = document.querySelector("#fixedCodePreview");

        if (!originalCodeElement || !patchedCodeElement) {
            alert("Could not retrieve original or patched code. Please try again.");
            return;
        }

        // Get code content and clean up any potential artifacts
        let originalCode = originalCodeElement.textContent.trim();
        let patchedCode = patchedCodeElement.textContent.trim();

        // Check if code appears to have line numbers (starting with 123456789...)
        if (patchedCode.startsWith("123456789") && patchedCode.includes("package")) {
            const codeStartIndex = patchedCode.indexOf("package");
            if (codeStartIndex > 0) {
                patchedCode = patchedCode.substring(codeStartIndex);
            }
        }

        try {
            const response = await fetch('/validate_patch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: filename,
                    bug_line: bugLine,
                    bug_type: bugType,
                    original_code: originalCode,
                    patched_code: patchedCode,
                    tool: tool
                })
            });

            const data = await response.json();

            // Create or get the validation results container
            let validationResultsDiv = document.getElementById('validationResults');
            if (!validationResultsDiv) {
                validationResultsDiv = document.createElement('div');
                validationResultsDiv.id = 'validationResults';
                document.querySelector('#fixedCodePreview').parentNode.insertBefore(
                    validationResultsDiv,
                    document.querySelector('#fixedCodePreview').nextSibling
                );
            }

            // Clear previous results
            validationResultsDiv.innerHTML = '';

            // Add validation message with status
            const messageDiv = document.createElement('div');
            messageDiv.className = `alert ${data.bug_fixed ? 'alert-success' : 'alert-danger'} fade show`;
            messageDiv.innerHTML = `<h6 class="mb-0">${data.message}</h6>`;
            validationResultsDiv.appendChild(messageDiv);

            // Automatically remove the message after 5 seconds
            setTimeout(() => {
                // Use Bootstrap's fade-out effect if available, otherwise just remove
                if (messageDiv.classList.contains('fade')) {
                    messageDiv.classList.remove('show');
                    // Wait for fade transition to complete before removing
                    messageDiv.addEventListener('transitionend', () => messageDiv.remove(), { once: true });
                } else {
                    messageDiv.remove();
                }
            }, 5000); // 5000 milliseconds = 5 seconds

            // Update bug count and UI only if the specific bug was fixed
            if (data.bug_fixed) {
                bugElement.remove();

                let currentBugCount = parseInt(bugsCountElement.textContent.replace("Bugs Detected: ", ""));
                let newBugCount = Math.max(0, currentBugCount - 1);
                bugsCountElement.textContent = `Bugs Detected: ${newBugCount}`;
            }

        } catch (error) {
            alert("Error validating bug. Please try again.");
        }
    }
});