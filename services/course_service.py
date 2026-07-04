"""Course service for managing courses and subjects using JSON file storage."""

import json
import os
import uuid
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


def _get_courses_file() -> str:
    """Get the path to the courses JSON file."""
    from config import Config
    return Config.COURSES_FILE


def _read_courses() -> List[Dict[str, Any]]:
    """Read all courses from the JSON file."""
    file_path = _get_courses_file()
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Error reading courses file: %s", e)
        return []


def _write_courses(courses: List[Dict[str, Any]]) -> bool:
    """Write courses list to the JSON file."""
    file_path = _get_courses_file()
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(courses, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        logger.error("Error writing courses file: %s", e)
        return False


def get_all_courses() -> List[Dict[str, Any]]:
    """Return a list of all courses."""
    return _read_courses()


def get_course_by_id(course_id: str) -> Optional[Dict[str, Any]]:
    """Return a single course by its ID, or None if not found."""
    courses = _read_courses()
    for course in courses:
        if course.get("course_id") == course_id:
            return course
    return None


def course_name_exists(course_name: str) -> bool:
    """Check if a course with the given name already exists (case-insensitive)."""
    courses = _read_courses()
    return any(
        c.get("course_name", "").strip().lower() == course_name.strip().lower()
        for c in courses
    )


def add_course(course_name: str, subjects: List[str]) -> Dict[str, Any]:
    """Add a new course with one or more subjects.

    Args:
        course_name: Name of the course.
        subjects: List of subject names.

    Returns:
        A dict with 'success' bool and either 'course' or 'error'.
    """
    course_name = course_name.strip()
    if not course_name:
        return {"success": False, "error": "Course name cannot be empty."}

    subjects = [s.strip() for s in subjects if s.strip()]
    if not subjects:
        return {"success": False, "error": "At least one subject is required."}

    if course_name_exists(course_name):
        return {"success": False, "error": f"Course '{course_name}' already exists."}

    courses = _read_courses()

    # Generate a unique course ID
    course_id = "C" + uuid.uuid4().hex[:6].upper()

    # Build subject list with unique IDs
    subject_list = [
        {"subject_id": "S" + uuid.uuid4().hex[:6].upper(), "subject_name": name}
        for name in subjects
    ]

    new_course = {
        "course_id": course_id,
        "course_name": course_name,
        "subjects": subject_list,
    }

    courses.append(new_course)
    if _write_courses(courses):
        return {"success": True, "course": new_course}
    return {"success": False, "error": "Failed to save course. Please try again."}


def add_subject_to_course(course_id: str, subject_name: str) -> Dict[str, Any]:
    """Add a new subject to an existing course.

    Args:
        course_id: The ID of the course.
        subject_name: Name of the subject to add.

    Returns:
        A dict with 'success' bool and either 'subject' or 'error'.
    """
    subject_name = subject_name.strip()
    if not subject_name:
        return {"success": False, "error": "Subject name cannot be empty."}

    courses = _read_courses()
    for course in courses:
        if course.get("course_id") == course_id:
            # Check for duplicate subject name in this course
            existing_names = [
                s.get("subject_name", "").strip().lower()
                for s in course.get("subjects", [])
            ]
            if subject_name.lower() in existing_names:
                return {
                    "success": False,
                    "error": f"Subject '{subject_name}' already exists in this course.",
                }

            new_subject = {
                "subject_id": "S" + uuid.uuid4().hex[:6].upper(),
                "subject_name": subject_name,
            }
            course.setdefault("subjects", []).append(new_subject)

            if _write_courses(courses):
                return {"success": True, "subject": new_subject}
            return {"success": False, "error": "Failed to save subject. Please try again."}

    return {"success": False, "error": f"Course with ID '{course_id}' not found."}


def delete_course(course_id: str) -> Dict[str, Any]:
    """Soft-delete a course by marking it as inactive.

    Checks if any active students are enrolled before deleting.

    Args:
        course_id: The ID of the course to delete.

    Returns:
        A dict with 'success' bool and optional 'error'.
    """
    from services.student_service import get_all_students

    courses = _read_courses()
    target_index = None
    for i, course in enumerate(courses):
        if course.get("course_id") == course_id:
            target_index = i
            break

    if target_index is None:
        return {"success": False, "error": f"Course '{course_id}' not found."}

    # Check for active enrolled students
    all_students = get_all_students()
    enrolled_active = [
        s for s in all_students
        if course_id in s.get("enrolled_courses", [])
        and s.get("is_active", True)
    ]
    if enrolled_active:
        count = len(enrolled_active)
        return {
            "success": False,
            "error": f"Cannot delete course: {count} active student(s) are enrolled.",
        }

    courses[target_index]["is_active"] = False
    if _write_courses(courses):
        return {"success": True}
    return {"success": False, "error": "Failed to delete course. Please try again."}


def update_course(course_id: str, updated_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing course's information.

    Args:
        course_id: The ID of the course to update.
        updated_data: Dict with fields to update (course_name, code, description, subjects).

    Returns:
        A dict with 'success' bool and either 'course' or 'error'.
    """
    courses = _read_courses()
    target_index = None
    for i, course in enumerate(courses):
        if course.get("course_id") == course_id:
            target_index = i
            break

    if target_index is None:
        return {"success": False, "error": f"Course '{course_id}' not found."}

    current_course = courses[target_index]

    course_name = updated_data.get("course_name", current_course.get("course_name", "")).strip()
    if not course_name:
        return {"success": False, "error": "Course name cannot be empty."}

    # Check for duplicate name (excluding current course)
    for i, c in enumerate(courses):
        if i == target_index:
            continue
        if c.get("course_name", "").strip().lower() == course_name.lower():
            return {"success": False, "error": f"Course name '{course_name}' already exists."}

    # Handle subjects update if provided
    subjects = updated_data.get("subjects", None)
    if subjects is not None:
        # subjects can be a list of names (strings) or list of dicts
        new_subjects = []
        existing_subjects = {s["subject_id"]: s for s in current_course.get("subjects", [])}
        for subj in subjects:
            if isinstance(subj, dict):
                # Preserve existing subject_id if available
                sid = subj.get("subject_id") or "S" + uuid.uuid4().hex[:6].upper()
                new_subjects.append({
                    "subject_id": sid,
                    "subject_name": subj.get("subject_name", "").strip(),
                })
            else:
                # String subject name - generate new ID
                new_subjects.append({
                    "subject_id": "S" + uuid.uuid4().hex[:6].upper(),
                    "subject_name": str(subj).strip(),
                })
        new_subjects = [s for s in new_subjects if s["subject_name"]]
    else:
        new_subjects = current_course.get("subjects", [])

    courses[target_index] = {
        **current_course,
        "course_name": course_name,
        "code": updated_data.get("code", current_course.get("code", "")),
        "description": updated_data.get("description", current_course.get("description", "")),
        "subjects": new_subjects,
    }

    if _write_courses(courses):
        return {"success": True, "course": courses[target_index]}
    return {"success": False, "error": "Failed to update course. Please try again."}
