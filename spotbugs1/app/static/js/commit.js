document.getElementById('commitChangesBtn').addEventListener('click', function () {
    // Create a modal dialog
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    `;

    // Create modal content
    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
        background: #2a2a40;
        padding: 20px;
        border-radius: 8px;
        width: 400px;
        color: #fff;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;

    // Add warning icon and title
    modalContent.innerHTML = `
        <div style="display: flex; align-items: center; margin-bottom: 15px;">
            <i class="fas fa-exclamation-triangle" style="color: #ffd700; margin-right: 10px;"></i>
            <h3 style="margin: 0;">Confirm Commit</h3>
        </div>
        <p style="margin-bottom: 15px;">Please review the following before committing:</p>
        <ul style="margin-bottom: 20px; padding-left: 20px;">
            <li>All bugs have been fixed and validated</li>
            <li>Changes have been tested</li>
            <li>The page will reload after committing</li>
        </ul>
        <div style="margin-bottom: 20px;">
            <label for="commitMessage" style="display: block; margin-bottom: 5px;">Commit Message:</label>
            <input type="text" id="commitMessage" class="form-control" 
                   value="Automated bug fixes applied" 
                   style="background: #1e272f; color: #fff; border: 1px solid #555;">
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button id="cancelCommit" class="btn btn-secondary">Cancel</button>
            <button id="confirmCommit" class="btn btn-primary">Commit Changes</button>
        </div>
    `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    // Handle cancel button
    document.getElementById('cancelCommit').addEventListener('click', function() {
        document.body.removeChild(modal);
    });

    // Handle confirm button
    document.getElementById('confirmCommit').addEventListener('click', function() {
        const commitMessage = document.getElementById('commitMessage').value;
        const repoUrl = document.getElementById('repo_url').value;

        fetch('/commit_changes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                commit_message: commitMessage,
                repo_url: repoUrl
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert(`Commit failed: ${data.message}`);
            }
        })
        .catch(error => {
            alert(`Commit failed: ${error}`);
            console.error("[Commit Error]", error);
        })
        .finally(() => {
            document.body.removeChild(modal);
        });
    });

    // Close modal when clicking outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
});
