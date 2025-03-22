document.addEventListener("DOMContentLoaded", function () {
    fetch(`${urlBase}/session/read/legacy-files`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.files_failed && data.files_failed.length > 0) {
            console.error("Failed to load files:", data.files_failed);
        }
        if (data.files_loaded >= 1) {
            location.reload();
        }
    })
    .catch(error => {
        console.error("Error loading legacy files:", error);
        console.error("Failed files (if any):", data?.files_failed || []);
    });
});

function deleteSession(sessionId) {
    if (confirm('Are you sure you want to delete this session?')) {
        fetch(`${urlBase}/session/${sessionId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (response.status !== 200) {
                alert('Failed to delete session.');
            } else {
                return response.json();
            }
        })
        .then(data => {
            if (Boolean(data)) {
                // Remove the session card from the DOM
                var sessionCard = document.getElementById('session-card-' + sessionId);
                if (sessionCard) {
                    sessionCard.parentNode.removeChild(sessionCard);
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
}
