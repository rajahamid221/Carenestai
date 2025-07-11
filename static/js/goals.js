document.addEventListener('DOMContentLoaded', function() {
    // --- Add Goal ---
    const addGoalForm = document.getElementById('addGoalForm');
    addGoalForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        const formData = new FormData(addGoalForm);
        const response = await fetch("{{ url_for('add_goal') }}", {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (result.success) {
            window.location.href = result.redirect_url;
        } else {
            alert('Error: ' + result.message);
        }
    });
    // --- Edit Goal ---
    const editGoalModal = document.getElementById('editGoalModal');
    editGoalModal.addEventListener('show.bs.modal', async function(event) {
        const button = event.relatedTarget;
        const goalId = button.dataset.goalId;
        const response = await fetch(`/api/goal/${goalId}`);
        const goal = await response.json();
        document.getElementById('editGoalId').value = goal.id;
        document.getElementById('editGoalTitle').value = goal.title;
        document.getElementById('editGoalDescription').value = goal.description;
        document.getElementById('editGoalTargetDate').value = goal.target_date;
        document.getElementById('editGoalStatus').value = goal.status;
    });
    const editGoalForm = document.getElementById('editGoalForm');
    editGoalForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        const goalId = document.getElementById('editGoalId').value;
        const formData = new FormData(editGoalForm);
        const response = await fetch(`/goals/${goalId}/edit`, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (result.success) {
            window.location.href = result.redirect_url;
        } else {
            alert('Error: ' + result.message);
        }
    });
    // --- Delete Goal ---
    const deleteGoalModal = document.getElementById('deleteGoalModal');
    let goalIdToDelete;
    // Initialize Bootstrap modal instance
    const bsDeleteGoalModal = new bootstrap.Modal(deleteGoalModal);
    deleteGoalModal.addEventListener('show.bs.modal', function(event) {
        const button = event.relatedTarget;
        goalIdToDelete = button.dataset.goalId;
    });
    const confirmDeleteGoalBtn = document.getElementById('confirmDeleteGoalBtn');
    confirmDeleteGoalBtn.addEventListener('click', async function() {
        try {
            const response = await fetch(`/api/goal/${goalIdToDelete}`, {
                method: 'DELETE'
            });
            const result = await response.json();
            if (result.success) {
                bsDeleteGoalModal.hide(); // Close the modal
                setTimeout(() => window.location.reload(), 300); // Wait for modal to close, then reload
            } else {
                alert('Error: ' + (result.message || 'Failed to delete goal.'));
            }
        } catch (err) {
            alert('An unexpected error occurred while deleting the goal.');
        }
    });
}); 