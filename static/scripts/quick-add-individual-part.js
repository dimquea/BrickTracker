// Quick Add Individual Part from Set Parts Table
// Handles the modal popup and form submission for adding individual parts

document.addEventListener('DOMContentLoaded', function() {
    // Get modal and form elements
    const modal = document.getElementById('quickAddIndividualPartModal');
    if (!modal) return; // Modal only exists on set details page

    const bsModal = new bootstrap.Modal(modal);
    const form = document.getElementById('quickAddForm');
    const submitBtn = document.getElementById('quickAddSubmit');

    // Handle click on quick-add buttons/links
    document.addEventListener('click', function(e) {
        const trigger = e.target.closest('.quick-add-individual-part');
        if (!trigger) return;

        // Prevent default link behavior if it's a dropdown item
        e.preventDefault();

        // Get part data from trigger attributes
        const partNumber = trigger.dataset.part;
        const colorId = trigger.dataset.color;
        const partName = trigger.dataset.name;
        const colorName = trigger.dataset.colorName;
        const imageUrl = trigger.dataset.image;

        // Populate modal with part info
        document.getElementById('quickAddPartImage').src = imageUrl;
        document.getElementById('quickAddPartName').textContent = partName;
        document.getElementById('quickAddPartNumber').textContent = `Part: ${partNumber}`;
        document.getElementById('quickAddPartColor').textContent = `Color: ${colorName}`;
        document.getElementById('quickAddPart').value = partNumber;
        document.getElementById('quickAddColor').value = colorId;

        // Reset form fields
        document.getElementById('quickAddQuantity').value = 1;
        document.getElementById('quickAddStorage').value = '';
        document.getElementById('quickAddPurchaseLocation').value = '';
        document.getElementById('quickAddDescription').value = '';

        // Show modal
        bsModal.show();
    });

    // Handle form submission
    submitBtn.addEventListener('click', async function() {
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        // Disable submit button to prevent double-submit
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Adding...';

        // Collect form data
        const formData = {
            part: document.getElementById('quickAddPart').value,
            color: document.getElementById('quickAddColor').value,
            quantity: parseInt(document.getElementById('quickAddQuantity').value),
            storage: document.getElementById('quickAddStorage').value || null,
            purchase_location: document.getElementById('quickAddPurchaseLocation').value || null,
            description: document.getElementById('quickAddDescription').value || null
        };

        try {
            // Submit to backend
            const response = await fetch(`${window.BK_ROOT || ""}/individual-parts/quick-add`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (response.ok) {
                // Success - show success message and close modal
                bsModal.hide();

                // Show success notification
                showNotification('success', `Added ${formData.quantity}x ${document.getElementById('quickAddPartName').textContent} to individual parts inventory`);

                // Optionally reload the page or update UI
                // window.location.reload();
            } else {
                // Error from server
                showNotification('error', result.error || 'Failed to add part to inventory');
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Add to Inventory';
            }
        } catch (error) {
            // Network or other error
            console.error('Error adding individual part:', error);
            showNotification('error', 'Network error. Please try again.');
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Add to Inventory';
        }
    });

    // Reset submit button when modal is hidden
    modal.addEventListener('hidden.bs.modal', function() {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Add to Inventory';
    });
});

// Helper function to show notifications
function showNotification(type, message) {
    // Create toast/alert element
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}
