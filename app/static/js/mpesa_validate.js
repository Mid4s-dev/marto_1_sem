/**
 * mpesa_validate.js — Real-time M-Pesa code format validation
 * Format: exactly 10 uppercase alphanumeric characters (^[A-Z0-9]{10}$)
 */
document.addEventListener('DOMContentLoaded', function () {
  const input = document.getElementById('mpesaCode');
  if (!input) return;

  const MPESA_RE = /^[A-Z0-9]{10}$/;

  input.addEventListener('input', function () {
    // Force uppercase
    input.value = input.value.toUpperCase().replace(/[^A-Z0-9]/g, '');

    if (MPESA_RE.test(input.value)) {
      input.classList.remove('is-invalid');
      input.classList.add('is-valid');
    } else {
      input.classList.remove('is-valid');
      if (input.value.length > 0) {
        input.classList.add('is-invalid');
      } else {
        input.classList.remove('is-invalid');
      }
    }
  });

  // Prevent form submit if invalid
  const form = document.getElementById('paymentForm');
  if (form) {
    form.addEventListener('submit', function (e) {
      if (!MPESA_RE.test(input.value)) {
        e.preventDefault();
        input.classList.add('is-invalid');
        input.focus();
      }
    });
  }
});
