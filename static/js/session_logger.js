document.addEventListener('DOMContentLoaded', function() {
    const logsContainer = document.getElementById('session-log-list-container');
    const templateLogRow = document.getElementById('session-log-row-template');
    const addLogRowButton = document.getElementById('add-session-log-row');
    const sessionForm = document.getElementById('session-log-form'); // Assuming form has this ID
    const sessionLogsJsonInput = document.getElementById('session_logs_json_data');
    const programSelect = document.getElementById('workout_program_id'); // ID of the program select field

    let exerciseOptions = [];
    const exercisesApiUrl = "/api/exercises"; // Centralized API endpoint for exercises

    // Fetch all exercises for dropdowns
    fetch(exercisesApiUrl)
        .then(response => response.json())
        .then(data => {
            exerciseOptions = data;
            // Populate template row's select once exercises are fetched
            if (templateLogRow) {
                 populateExerciseSelect(templateLogRow.querySelector('.exercise-select'));
            }

            // Handle pre-filling from existing session_logs_json_data if editing
            const existingLogsDataAttr = sessionForm ? sessionForm.dataset.existingLogs : null;
            let existingLogs = null;
            if (existingLogsDataAttr && existingLogsDataAttr !== 'null') {
                try {
                    existingLogs = JSON.parse(existingLogsDataAttr);
                } catch (e) {
                    console.error("Error parsing existing session logs data:", e);
                }
            }

            if (existingLogs && existingLogs.logs && existingLogs.logs.length > 0) {
                existingLogs.logs.forEach(log => addSessionLogRow(log));
            } else {
                // Add one empty row by default if creating new and no existing data
                if (logsContainer && !logsContainer.querySelector('.session-log-row')) {
                    addSessionLogRow();
                }
            }
        })
        .catch(error => console.error('Error fetching exercises:', error));

    function populateExerciseSelect(selectElement) {
        if (!selectElement) return;
        selectElement.querySelectorAll('option:not([disabled])').forEach(o => o.remove());
        exerciseOptions.forEach(ex => {
            const option = document.createElement('option');
            option.value = ex.id;
            option.textContent = ex.name;
            selectElement.appendChild(option);
        });
    }

    function addSessionLogRow(logData = {}) {
        if (!templateLogRow || !logsContainer) return;

        const newRow = templateLogRow.cloneNode(true);
        newRow.id = '';
        newRow.style.display = 'grid'; // Or your desired display style
        newRow.classList.add('session-log-row'); // Add class for easier selection

        const exerciseSelect = newRow.querySelector('.exercise-select');
        populateExerciseSelect(exerciseSelect);
        if (logData.exercise_id) {
            exerciseSelect.value = logData.exercise_id;
        }

        // TODO: Add dynamic set logging within each exercise row
        // For now, simple fields per exercise log
        newRow.querySelector('.log-reps-input').value = logData.reps || '';
        newRow.querySelector('.log-weight-input').value = logData.weight || '';
        newRow.querySelector('.log-set-rpe-input').value = logData.set_rpe || '';
        newRow.querySelector('.log-notes-input').value = logData.notes || '';


        newRow.querySelector('.remove-log-row-btn').addEventListener('click', function() {
            newRow.remove();
        });

        logsContainer.appendChild(newRow);
    }

    if (addLogRowButton) {
        addLogRowButton.addEventListener('click', () => addSessionLogRow());
    }

    // TODO: Listener for programSelect change to fetch program exercises
    if (programSelect) {
        programSelect.addEventListener('change', function() {
            const programId = this.value;
            if (programId) {
                fetchProgramExercises(programId);
            } else {
                // Clear existing logs or ask user?
                clearLogRows();
                addSessionLogRow(); // Add a default blank row
            }
        });
    }

    function clearLogRows() {
        if (!logsContainer) return;
        logsContainer.querySelectorAll('.session-log-row').forEach(row => row.remove());
    }

    async function fetchProgramExercises(programId) {
        try {
            // This API endpoint needs to be created
            const response = await fetch(`/api/workout_programs/${programId}/exercises_detailed`);
            if (!response.ok) {
                console.error("Failed to fetch program exercises:", response.statusText);
                flashMessage("Could not load exercises for the selected program.", "warning");
                return;
            }
            const programDetails = await response.json();

            clearLogRows(); // Clear existing rows before populating

            if (programDetails && programDetails.exercises_json && programDetails.exercises_json.exercises) {
                programDetails.exercises_json.exercises.forEach(exerciseDetail => {
                    // The logData structure for addSessionLogRow might need adjustment
                    // to match how program exercises are structured vs how logs are structured.
                    // For now, let's assume a simple mapping.
                    addSessionLogRow({
                        exercise_id: exerciseDetail.exercise_id,
                        // Pre-fill other fields if available, e.g., reps/sets from program
                        // This part needs careful thought on how program structure maps to log structure
                        reps: exerciseDetail.reps, // Example
                        notes: `Programmed: ${exerciseDetail.sets} sets of ${exerciseDetail.reps}`
                    });
                });
            } else {
                 addSessionLogRow(); // Add a default blank row if program has no exercises
            }
        } catch (error) {
            console.error('Error fetching program exercises:', error);
            flashMessage("Error loading program exercises. Please add manually.", "danger");
        }
    }


    if (sessionForm) {
        sessionForm.addEventListener('submit', function(event) {
            const sessionLogs = [];
            logsContainer.querySelectorAll('.session-log-row').forEach(row => {
                const logEntry = {
                    exercise_id: row.querySelector('.exercise-select').value,
                    // This structure will need to be more complex to support multiple sets per exercise
                    // For now, a simplified single entry per exercise:
                    reps: row.querySelector('.log-reps-input').value,
                    weight: row.querySelector('.log-weight-input').value,
                    set_rpe: row.querySelector('.log-set-rpe-input').value,
                    notes: row.querySelector('.log-notes-input').value,
                    // TODO: Add structure for multiple sets, e.g.
                    // sets_logs: [ {set_number: 1, reps: ..., weight: ...}, ... ]
                };
                if (logEntry.exercise_id) { // Only add if an exercise is selected
                    sessionLogs.push(logEntry);
                }
            });
            sessionLogsJsonInput.value = JSON.stringify({ logs: sessionLogs });
        });
    }

    // Helper for flashing messages (requires a #flash-messages container in layout)
    function flashMessage(message, category = 'info') {
        const flashContainer = document.getElementById('flash-messages-js'); // Specific container for JS flashes
        if (flashContainer) {
            const alert = `
                <div class="alert alert-${category} alert-dismissible fade show m-3" role="alert">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>`;
            flashContainer.innerHTML += alert;
        }
    }
});
