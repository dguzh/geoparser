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
