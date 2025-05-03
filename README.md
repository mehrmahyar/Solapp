# SOLAPP - Strength & Conditioning Management App

This is a local web application built with Flask to manage strength and conditioning data for teams and players.

## Features

*   Team and Player Management
*   Health Questionnaires
*   Progress Photo Uploads
*   Body Composition Tracking
*   Physical Test Logging (including Baselines)
*   Exercise Library Management
*   Workout Program Creation & Assignment
*   Training Session Logging
*   Daily Readiness Monitoring & Scoring
*   PDF Report Generation (Players & Teams)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install WeasyPrint System Dependencies:**
    This is crucial for PDF generation. Follow the instructions for your operating system:
    *   **macOS:** `brew install pango gdk-pixbuf cairo libffi`
    *   **Debian/Ubuntu:** `sudo apt-get update && sudo apt-get install python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info`
    *   **Fedora:** `sudo dnf install python3-devel python3-pip python3-setuptools python3-wheel python3-cffi cairo pango gdk-pixbuf2 libffi-devel`
    *   **Windows:** See [WeasyPrint Windows Installation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows)

5.  **Initialize the database (if using migrations):**
    ```bash
    # Set the FLASK_APP environment variable (optional if using app.py directly)
    # export FLASK_APP=app.py # Linux/macOS
    # $env:FLASK_APP = "app.py" # Windows PowerShell
    # set FLASK_APP=app.py # Windows CMD

    flask db init  # Run only once to initialize migrations
    flask db migrate -m "Initial database schema" # Run when models change
    flask db upgrade # Apply migrations
    ```
    *Note: For this simple setup, `db.create_all()` in `app.py` might suffice, but migrations are better practice.*

6.  **Run the application:**
    ```bash
    python app.py
    ```
    Or using the Flask CLI:
    ```bash
    flask run
    ```

7.  **Access the app:** Open your web browser and go to `http://127.0.0.1:5000`

## Notes

*   The application uses a local SQLite database (`instance/solapp.db`).
*   Uploaded photos are stored in the `uploads/` directory.
*   Temporary plot images for PDF reports are stored in `instance/plot_images/`.
*   JSON fields are used for flexibility in storing questionnaire responses, workout structures, and session logs. Ensure valid JSON when editing these manually in forms.
*   Readiness score weights are currently defined in `config.py`.
*   The `kaleido` package is used by Plotly to export static images for PDF reports. 