# Student Results Management System

A Flask-based web application for managing student academic results with an admin panel.

## Features

### Student Side
- View results by entering seat number
- See grades for all subjects
- Automatic pass/fail status calculation

### Admin Panel
- Secure login system
- Upload grades via Excel file
- Manually add/edit students and grades
- View all students and their results
- Bulk delete grades

## Setup Instructions

1. Create a virtual environment (recommended):
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Access the application:
- Open http://localhost:5000 in your browser
- Student portal is available at the home page
- Admin panel is at http://localhost:5000/admin/login

## Default Admin Credentials
- Username: admin
- Password: admin123

**Important:** Change the default password after first login for security.

## Excel File Format
When uploading grades via Excel file, ensure the following columns are present:
- seat_number: Student's seat number
- name: Student's full name
- subject: Subject name
- grade: Grade value (A+, A, B+, B, C, or F)

## Directory Structure
```
.
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── templates/         # HTML templates
├── static/           # CSS, JS, and other static files
├── uploads/         # Uploaded Excel files
└── backups/         # Data backups
```

## Grade Scale
- A+: Excellent
- A: Very Good
- B+: Good
- B: Above Average
- C: Average
- F: Fail

## Security Notes
1. Change the default admin password
2. Update the SECRET_KEY in app.py
3. Enable HTTPS in production
4. Regularly backup the database 