# Project Update - 24.12.2025

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

# Project Update - 28.12.2025
### Database and User Management
- Created a database and collections using MongoDB.
- Added user registration functionality to the collection.
- Implemented login/logout routes for registered users.


# Project Update - 28.12.2025
### Login Flow Improvements
- Added proper error handling for failed login attempts
- Re-rendered the login page with an inline error message on failure
- Preserved POST-back behavior so the form submits to the same endpoint
- Improved session handling for authenticated routes

### Dashboard Route Enhancements
- Added session validation to restrict dashboard access to logged-in users
- Passed username, user ID, and doctor metadata from the session into the dashboard
- Structured the route to support dynamic data loading from MongoDB

### MongoDB Configuration Refactor
- Centralized environment variable loading at module level
- Created a reusable MongoDB client and collection reference
- Reduced repeated I/O and improved maintainability of database operations
- Ensured database configuration is globally accessible across functions

### Dynamic Clinic Dashboard
- Implemented a query to fetch all clinics associated with the logged-in doctor
- Integrated clinic data into the dashboard template for dynamic rendering
- Replaced static HTML with a data-driven layout while preserving all CSS classes
- Displayed all relevant clinic fields based on the actual MongoDB schema
- Ensured the UI remains visually identical while becoming fully dynamic

### Schema Integration and Data Mapping
- Mapped real MongoDB fields such as clinic details, doctor information, visit days, and contact data
- Ensured displayed values align with the existing schema structure
- Maintained consistency between backend data and frontend presentation