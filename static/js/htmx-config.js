// HTMX Configuration and Modal Handling

// Open modal function
function openModal(content) {
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = content;
    modal.classList.add('show');
}

// Close modal function
function closeModal() {
    const modal = document.getElementById('modal');
    modal.classList.remove('show');
    document.getElementById('modal-body').innerHTML = '';
}

// HTMX Event Listeners
document.addEventListener('DOMContentLoaded', function () {

    // Handle modal forms
    document.body.addEventListener('htmx:afterSwap', function (event) {
        // If response is a form, open it in modal
        if (event.detail.target.id === 'modal-body') {
            openModal(event.detail.target.innerHTML);
        }
    });

    // Close modal on successful form submission
    document.body.addEventListener('htmx:afterRequest', function (event) {
        if (event.detail.successful && event.detail.xhr.status === 200) {
            // Check if it was a form submission
            const isFormSubmit = event.detail.requestConfig.verb === 'post' ||
                event.detail.requestConfig.verb === 'put';

            if (isFormSubmit) {
                closeModal();
            }
        }
    });

    // Handle delete confirmations
    document.body.addEventListener('click', function (event) {
        if (event.target.classList.contains('delete-btn')) {
            if (!confirm('Are you sure you want to delete this item?')) {
                event.preventDefault();
                event.stopPropagation();
            }
        }
    });

    // Auto-hide messages after 5 seconds
    setTimeout(function () {
        const messages = document.querySelectorAll('.alert');
        messages.forEach(function (message) {
            message.style.transition = 'opacity 0.5s';
            message.style.opacity = '0';
            setTimeout(function () {
                message.remove();
            }, 500);
        });
    }, 5000);

    // Close modal when clicking outside
    document.getElementById('modal').addEventListener('click', function (event) {
        if (event.target === this) {
            closeModal();
        }
    });
});

// Helper function to update product price in invoice form
function updateProductPrice(selectElement) {
    const selectedOption = selectElement.options[selectElement.selectedIndex];
    const price = selectedOption.dataset.price;
    const priceInput = selectElement.closest('.formset-row').querySelector('input[name$="-unit_price"]');
    if (price && priceInput) {
        priceInput.value = price;
    }
}
