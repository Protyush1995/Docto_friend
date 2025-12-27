# Project Name : DOCTOPAL

## Changes Made

### Doctor Seed Submission Route (`/doctor-seed`)
- Handles POST requests to save doctor information from the form.
- Collects data, generates a QR code filename, and stores data in a session.
- Returns success messages with a link to the dashboard.

### Dashboard Route (`/doc-seed-dashboard`)
- Displays the last submitted doctor's data.
- Renders dynamic information within the dashboard view.

### HTML Template Updates
- Updated `doctor_db_seed.html` to include a "Go to Dashboard" button, allowing navigation post-submission and conditionally displaying success/error messages.
- Modified `dashboard.html` to populate the profile card with doctor data dynamically.
- In `index.html`, added two options for improved navigation:

