"""Application configuration for the Flask Result Management System."""

import os


class Config:
    """Base configuration class."""

    # Flask secret key for session management
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "rms-secret-key-change-in-production")

    # Base directory of the application
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))

    # Data directory for JSON storage
    DATA_DIR: str = os.path.join(BASE_DIR, "data")

    # JSON data file paths
    COURSES_FILE: str = os.path.join(DATA_DIR, "courses.json")
    STUDENTS_FILE: str = os.path.join(DATA_DIR, "students.json")
    MARKS_FILE: str = os.path.join(DATA_DIR, "marks.json")

    # Admin credentials (use environment variables in production)
    ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "admin123")

    # Debug mode
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
