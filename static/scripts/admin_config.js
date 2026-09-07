// Admin Configuration Management
// Handles live environment variable configuration interface

// Initialize form values with current configuration
function initializeConfigValues() {
  console.log('Initializing config values with:', window.CURRENT_CONFIG);

  Object.keys(window.CURRENT_CONFIG).forEach(varName => {
    const value = window.CURRENT_CONFIG[varName];
    console.log(`Setting ${varName} = ${value}`);

    // Handle live settings (checkboxes and inputs)
    const liveToggle = document.getElementById(varName);
    if (liveToggle && liveToggle.type === 'checkbox') {
      liveToggle.checked = value === true;
      console.log(`Set checkbox ${varName} to ${value}`);
    }

    const liveInputs = document.querySelectorAll(`input[data-var="${varName}"]:not(.config-static)`);
    liveInputs.forEach(input => {
      if (input.type !== 'checkbox') {
        input.value = value !== null && value !== undefined ? value : '';
        console.log(`Set input ${varName} to ${input.value}`);
      }
    });

    // Handle static settings
    const staticToggle = document.getElementById(`static-${varName}`);
    if (staticToggle && staticToggle.type === 'checkbox') {
      staticToggle.checked = value === true;
      console.log(`Set static checkbox ${varName} to ${value}`);
    }

    const staticInputs = document.querySelectorAll(`input[data-var="${varName}"].config-static`);
    staticInputs.forEach(input => {
      if (input.type !== 'checkbox') {
        input.value = value !== null && value !== undefined ? value : '';
        console.log(`Set static input ${varName} to ${input.value}`);
      }
    });
  });
}

// Handle config change events
function handleConfigChange(element) {
  const varName = element.dataset.var;
  let newValue;

  if (element.type === 'checkbox') {
    newValue = element.checked;
  } else if (element.type === 'number') {
    newValue = parseInt(element.value) || 0;
  } else {
    newValue = element.value;
  }

  // Update the badge display
  updateConfigBadge(varName, newValue);

  // Note: Changes are only saved when "Save All Changes" button is clicked
}

// Update badge display
function updateConfigBadge(varName, value) {
  const defaultValue = window.DEFAULT_CONFIG[varName];
  const isChanged = JSON.stringify(value) !== JSON.stringify(defaultValue);

  // Remove existing badges but keep them inline
  const existingBadges = document.querySelectorAll(`[data-badge-var="${varName}"]`);
  existingBadges.forEach(badge => {
    badge.remove();
  });

  // Find the label where we should insert new badges
  const label = document.querySelector(`label[for="${varName}"], label[for="static-${varName}"]`);
  if (!label) return;

  // Find the description div (with .text-muted class) to insert badges before it
  const descriptionDiv = label.querySelector('.text-muted');

  // Create value badge based on new logic
  let valueBadge;
  if (value === true) {
    valueBadge = document.createElement('span');
    valueBadge.className = 'badge rounded-pill text-bg-success ms-2';
    valueBadge.textContent = 'True';
    valueBadge.setAttribute('data-badge-var', varName);
    valueBadge.setAttribute('data-badge-type', 'value');
  } else if (value === false) {
    valueBadge = document.createElement('span');
    valueBadge.className = 'badge rounded-pill text-bg-danger ms-2';
    valueBadge.textContent = 'False';
    valueBadge.setAttribute('data-badge-var', varName);
    valueBadge.setAttribute('data-badge-type', 'value');
  } else if (JSON.stringify(value) === JSON.stringify(defaultValue)) {
    valueBadge = document.createElement('span');
    valueBadge.className = 'badge rounded-pill text-bg-light text-dark ms-2';
    valueBadge.textContent = `Default: ${defaultValue}`;
    valueBadge.setAttribute('data-badge-var', varName);
    valueBadge.setAttribute('data-badge-type', 'value');
  } else {
    // For text/number fields that have been changed, show "Default: X"
    valueBadge = document.createElement('span');
    valueBadge.className = 'badge rounded-pill text-bg-light text-dark ms-2';
    valueBadge.textContent = `Default: ${defaultValue}`;
    valueBadge.setAttribute('data-badge-var', varName);
    valueBadge.setAttribute('data-badge-type', 'value');
  }

  // Insert badge before the description div (to keep it on same line as title)
  if (descriptionDiv) {
    label.insertBefore(valueBadge, descriptionDiv);
  } else {
    label.appendChild(valueBadge);
  }

  // Add changed badge if needed
  if (isChanged) {
    const changedBadge = document.createElement('span');
    changedBadge.className = 'badge rounded-pill text-bg-warning ms-1';
    changedBadge.textContent = 'Changed';
    changedBadge.setAttribute('data-badge-var', varName);
    changedBadge.setAttribute('data-badge-type', 'changed');

    // Insert changed badge after the value badge
    if (descriptionDiv) {
      label.insertBefore(changedBadge, descriptionDiv);
    } else {
      label.appendChild(changedBadge);
    }
  }
}

// Handle static config save
function saveStaticConfig() {
  const staticInputs = document.querySelectorAll('.config-static, .config-static-toggle');
  const updates = {};

  staticInputs.forEach(input => {
    const varName = input.dataset.var;
    let value;

    if (input.type === 'checkbox') {
      value = input.checked;
    } else {
      value = input.value;
    }

    updates[varName] = value;
  });

  console.log('Saving static config:', updates);

  // Send to backend via fetch API
  fetch(`${window.BK_ROOT || ""}/admin/api/config/update-static`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ updates: updates })
  })
  .then(response => response.json())
  .then(data => {
    const statusContainer = document.getElementById('config-status');
    if (statusContainer) {
      if (data.status === 'success') {
        statusContainer.innerHTML = '<div class="alert alert-success"><i class="ri-check-line"></i> Static configuration saved to .env file!</div>';
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => {
          statusContainer.innerHTML = '';
        }, 3000);
      } else {
        statusContainer.innerHTML = `<div class="alert alert-danger"><i class="ri-error-warning-line"></i> Error: ${data.message || 'Failed to save static configuration'}</div>`;
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }
  })
  .catch(error => {
    console.error('Save static config error:', error);
    const statusContainer = document.getElementById('config-status');
    if (statusContainer) {
      statusContainer.innerHTML = '<div class="alert alert-danger"><i class="ri-error-warning-line"></i> Error: Failed to save static configuration</div>';
    }
  });
}

// Handle button functionality
function setupButtonHandlers() {
  // Save All Changes button
  const saveAllBtn = document.getElementById('config-save-all');
  if (saveAllBtn) {
    saveAllBtn.addEventListener('click', () => {
      console.log('Save All Changes clicked');
      saveLiveConfiguration();
    });
  }

  // Refresh button
  const refreshBtn = document.getElementById('config-refresh');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      console.log('Refresh clicked');
      location.reload();
    });
  }

  // Reset button. Opens Bootstrap modal instead of browser confirm()
  const resetBtn = document.getElementById('config-reset');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      const modal = new bootstrap.Modal(document.getElementById('resetDefaultsModal'));
      modal.show();
    });
  }

  // Confirm reset inside the modal
  const confirmResetBtn = document.getElementById('confirm-reset-defaults');
  if (confirmResetBtn) {
    confirmResetBtn.addEventListener('click', () => {
      resetToDefaults();
    });
  }

  // Static config save button
  const saveStaticBtn = document.getElementById('config-save-static');
  if (saveStaticBtn) {
    saveStaticBtn.addEventListener('click', saveStaticConfig);
  }
}

// Save live configuration changes
function saveLiveConfiguration() {
  const liveInputs = document.querySelectorAll('.config-toggle, .config-number, .config-text');
  const updates = {};

  liveInputs.forEach(input => {
    const varName = input.dataset.var;
    let value;

    if (input.type === 'checkbox') {
      value = input.checked;
    } else if (input.type === 'number') {
      value = parseInt(input.value) || 0;
    } else {
      value = input.value;
    }

    updates[varName] = value;
  });

  console.log('Saving live configuration:', updates);

  // Show status message
  const statusContainer = document.getElementById('config-status');
  if (statusContainer) {
    statusContainer.innerHTML = '<div class="alert alert-info"><i class="ri-loader-4-line"></i> Saving configuration...</div>';
  }

  // Send to backend via fetch API
  fetch(`${window.BK_ROOT || ""}/admin/api/config/update`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ updates: updates })
  })
  .then(response => response.json())
  .then(data => {
    if (statusContainer) {
      if (data.status === 'success') {
        statusContainer.innerHTML = '<div class="alert alert-success"><i class="ri-check-line"></i> Configuration saved successfully! Reloading page...</div>';

        // Reload the page after a short delay
        setTimeout(() => {
          location.reload();
        }, 1000);
      } else {
        statusContainer.innerHTML = `<div class="alert alert-danger"><i class="ri-error-warning-line"></i> Error: ${data.message || 'Failed to save configuration'}</div>`;
      }
    }
  })
  .catch(error => {
    console.error('Save error:', error);
    if (statusContainer) {
      statusContainer.innerHTML = '<div class="alert alert-danger"><i class="ri-error-warning-line"></i> Error: Failed to save configuration</div>';
    }
  });
}

// Reset all settings to defaults
function resetToDefaults() {
  console.log('Resetting to defaults');

  Object.keys(window.DEFAULT_CONFIG).forEach(varName => {
    const defaultValue = window.DEFAULT_CONFIG[varName];

    const toggle = document.getElementById(varName);
    if (toggle && toggle.type === 'checkbox') {
      toggle.checked = defaultValue === true;
    }

    document.querySelectorAll(`input[data-var="${varName}"]:not(.config-static)`).forEach(input => {
      if (input.type !== 'checkbox') {
        input.value = defaultValue !== null && defaultValue !== undefined ? defaultValue : '';
      }
    });

    updateConfigBadge(varName, defaultValue);
  });

  // Show status message
  const statusContainer = document.getElementById('config-status');
  if (statusContainer) {
    statusContainer.innerHTML = '<div class="alert alert-warning"><i class="ri-restart-line"></i> Settings reset to defaults. Click "Save All Changes" to apply.</div>';
  }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  console.log('DOM loaded, initializing configuration interface');

  // Initialize form values
  initializeConfigValues();

  // Setup button handlers
  setupButtonHandlers();

  // Set up event listeners for form changes
  document.addEventListener('change', (e) => {
    if (e.target.matches('[data-var]')) {
      handleConfigChange(e.target);
    }
  });

  console.log('Configuration interface initialized - ready for API calls');
});