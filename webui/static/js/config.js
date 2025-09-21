document.addEventListener('DOMContentLoaded', function() {
    // Set current logging level
    const loggingLevel = document.getElementById('loggingLevel');
    if (loggingLevel) {
        const currentLevel = config.logging_level || 'INFO';
        loggingLevel.value = currentLevel;
    }

    // Add change handler to show unsaved changes warning
    loggingLevel.addEventListener('change', function() {
        document.getElementById('unsavedChanges').style.display = 'block';
    });
});