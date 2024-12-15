function deleteSession(sessionId) {
    if (confirm('Are you sure you want to delete this session?')) {
        fetch(Flask.url_for('delete_session', {session_id:''}) + sessionId, {
            method: 'POST'
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
            } else {
                return response.json();
            }
        })
        .then(data => {
            if (data.status === 'success') {
                // Remove the session card from the DOM
                var sessionCard = document.getElementById('session-card-' + sessionId);
                if (sessionCard) {
                    sessionCard.parentNode.removeChild(sessionCard);
                }
            } else {
                alert('Failed to delete session.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
}
