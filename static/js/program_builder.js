document.addEventListener('DOMContentLoaded', function() {
    const exercisesContainer = document.getElementById('exercise-list-container');
    const templateRow = document.getElementById('exercise-row-template');
    const addRowButton = document.getElementById('add-exercise-row');
    const programForm = document.getElementById('program-form');
    const exercisesJsonInput = document.getElementById('exercises-json-data');

    // --- Read existing program data from data attribute --- 
    let existingProgramData = null;
    const existingDataAttr = programForm.dataset.existingProgram;
    if (existingDataAttr && existingDataAttr !== 'null') {
        try {
            existingProgramData = JSON.parse(existingDataAttr);
        } catch (e) {
            console.error("Error parsing existing program data:", e);
        }
    }
    // --- API URL (assuming it might be needed, keep if necessary) ---
    // If exercisesApiUrl was defined in the template, find a way to pass it
    // e.g., another data attribute on the form or container
    const exercisesApiUrl = "/api/exercises"; // Hardcoding for now, update if needed

    let exerciseOptions = [];

    // Fetch exercises for dropdown
    fetch(exercisesApiUrl)
        .then(response => response.json())
        .then(data => {
            exerciseOptions = data;
            // Populate existing rows if editing
            if (existingProgramData && existingProgramData.exercises) {
                existingProgramData.exercises.forEach(ex => addExerciseRow(ex));
            } else {
                // Add one empty row by default if creating new
                if (!exercisesContainer.querySelector('.exercise-row')) {
                     addExerciseRow();
                }
            }
             // Ensure template select is populated even if no initial rows
             populateExerciseSelect(templateRow.querySelector('.exercise-select'));
        })
        .catch(error => console.error('Error fetching exercises:', error));

    // Function to populate exercise dropdown
    function populateExerciseSelect(selectElement) {
        // Clear existing options except placeholder
        selectElement.querySelectorAll('option:not([disabled])').forEach(o => o.remove());
        exerciseOptions.forEach(ex => {
            const option = document.createElement('option');
            option.value = ex.id;
            option.textContent = ex.name;
            selectElement.appendChild(option);
        });
    }

    // Function to add a new exercise row
    function addExerciseRow(exerciseData = {}) {
        const newRow = templateRow.cloneNode(true);
        newRow.id = ''; // Remove template ID
        newRow.style.display = 'grid'; // Use grid layout

        const exerciseSelect = newRow.querySelector('.exercise-select');
        populateExerciseSelect(exerciseSelect);

        // Set values if editing or pre-populating
        exerciseSelect.value = exerciseData.exercise_id || '';
        newRow.querySelector('.category-select').value = exerciseData.category || '';
        newRow.querySelector('.sets-input').value = exerciseData.sets || '';
        newRow.querySelector('.reps-input').value = exerciseData.reps || '';
        newRow.querySelector('.rest-input').value = exerciseData.rest || '';
        newRow.querySelector('.notes-input').value = exerciseData.exercise_notes || ''; // Match name attr

        // Add event listener for remove button
        newRow.querySelector('.remove-exercise-btn').addEventListener('click', function() {
            newRow.remove();
        });

        exercisesContainer.appendChild(newRow);
    }

    // Event listener for adding a row
    addRowButton.addEventListener('click', () => addExerciseRow());

    // Event listener for form submission
    programForm.addEventListener('submit', function(event) {
        const exercises = [];
        exercisesContainer.querySelectorAll('.exercise-row:not(#exercise-row-template)').forEach(row => {
            const exercise = {
                exercise_id: row.querySelector('.exercise-select').value,
                category: row.querySelector('.category-select').value,
                sets: row.querySelector('.sets-input').value,
                reps: row.querySelector('.reps-input').value,
                rest: row.querySelector('.rest-input').value,
                exercise_notes: row.querySelector('.notes-input').value // Match name attr
            };

            // Basic validation: Ensure exercise ID is selected
            if (!exercise.exercise_id) {
                // Optionally add validation feedback
                console.warn("Skipping row with no exercise selected.");
                return; // Skip this row
            }
            exercises.push(exercise);
        });

        // Store the structured data as JSON in the hidden field
        exercisesJsonInput.value = JSON.stringify({ exercises: exercises });
        // Allow form submission to proceed
    });

}); 