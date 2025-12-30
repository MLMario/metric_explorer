/**
 * Metric Drill-Down Agent - Client-side JavaScript
 * Minimal JS for file preview and markdown rendering
 */

// Import marked for markdown rendering (loaded via CDN in views that need it)
// const marked = window.marked;

/**
 * Initialize app when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
  initFileUpload();
  initMarkdownRendering();
  initFormValidation();
});

/**
 * File upload handling
 */
function initFileUpload() {
  const fileInputs = document.querySelectorAll('input[type="file"]');

  fileInputs.forEach(input => {
    input.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        validateFile(file, input);
      }
    });
  });
}

/**
 * Validate file before upload
 */
function validateFile(file, input) {
  const maxSize = 50 * 1024 * 1024; // 50MB
  const allowedTypes = ['.csv', 'text/csv', 'application/csv'];

  // Check file size
  if (file.size > maxSize) {
    showError(input, 'File exceeds maximum size of 50MB');
    input.value = '';
    return false;
  }

  // Check file type
  const ext = file.name.toLowerCase().split('.').pop();
  if (ext !== 'csv') {
    showError(input, 'Only CSV files are accepted');
    input.value = '';
    return false;
  }

  clearError(input);
  return true;
}

/**
 * Show error message for form field
 */
function showError(input, message) {
  const formGroup = input.closest('.form-group');
  if (!formGroup) return;

  // Remove existing error
  const existingError = formGroup.querySelector('.form-error');
  if (existingError) existingError.remove();

  // Add error class to input
  input.classList.add('error');

  // Add error message
  const errorEl = document.createElement('p');
  errorEl.className = 'form-error';
  errorEl.textContent = message;
  formGroup.appendChild(errorEl);
}

/**
 * Clear error message for form field
 */
function clearError(input) {
  const formGroup = input.closest('.form-group');
  if (!formGroup) return;

  input.classList.remove('error');
  const existingError = formGroup.querySelector('.form-error');
  if (existingError) existingError.remove();
}

/**
 * Markdown rendering for report display
 */
function initMarkdownRendering() {
  const markdownContainers = document.querySelectorAll('[data-markdown]');

  markdownContainers.forEach(container => {
    if (window.marked) {
      const content = container.textContent;
      container.innerHTML = window.marked.parse(content);
    }
  });
}

/**
 * Form validation
 */
function initFormValidation() {
  const forms = document.querySelectorAll('form[data-validate]');

  forms.forEach(form => {
    form.addEventListener('submit', (e) => {
      const requiredFields = form.querySelectorAll('[required]');
      let valid = true;

      requiredFields.forEach(field => {
        if (!field.value.trim()) {
          showError(field, 'This field is required');
          valid = false;
        } else {
          clearError(field);
        }
      });

      if (!valid) {
        e.preventDefault();
      }
    });
  });
}

/**
 * HTMX event handlers
 */

// Handle HTMX request errors
document.body.addEventListener('htmx:responseError', (e) => {
  console.error('HTMX error:', e.detail);
  const target = e.detail.target;
  if (target) {
    target.innerHTML = `
      <div class="alert alert-error">
        An error occurred. Please try again.
      </div>
    `;
  }
});

// Handle HTMX before request (show loading)
document.body.addEventListener('htmx:beforeRequest', (e) => {
  const indicator = e.detail.elt.querySelector('.htmx-indicator');
  if (indicator) {
    indicator.style.display = 'inline-block';
  }
});

// Handle HTMX after request (hide loading)
document.body.addEventListener('htmx:afterRequest', (e) => {
  const indicator = e.detail.elt.querySelector('.htmx-indicator');
  if (indicator) {
    indicator.style.display = 'none';
  }
});
