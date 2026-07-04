"""Marks service for managing marks submission and result publication."""

import json
import os
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


def _get_marks_file() -> str:
    """Get the path to the marks JSON file."""
    from config import Config
    return Config.MARKS_FILE


def _read_marks() -> List[Dict[str, Any]]:
    """Read all marks records from the JSON file."""
    file_path = _get_marks_file()
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Error reading marks file: %s", e)
        return []


def _write_marks(marks: List[Dict[str, Any]]) -> bool:
    """Write marks list to the JSON file."""
    file_path = _get_marks_file()
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(marks, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        logger.error("Error writing marks file: %s", e)
        return False


def get_marks_record(
    roll_no: str, course_id: str
) -> Optional[Dict[str, Any]]:
    """Return the marks record for a student in a course, or None."""
    all_marks = _read_marks()
    for record in all_marks:
        if record.get("roll_no") == roll_no and record.get("course_id") == course_id:
            return record
    return None


def get_all_marks() -> List[Dict[str, Any]]:
    """Return all marks records."""
    return _read_marks()


def submit_marks(
    roll_no: str,
    course_id: str,
    marks_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Submit or update marks for a student in a course.

    Marks can be updated multiple times before publishing.
    Marks entry is only allowed if the student is enrolled in the course.

    Args:
        roll_no: Student's roll number.
        course_id: Course ID.
        marks_data: List of dicts with keys: subject_id, marks_obtained, max_marks.

    Returns:
        A dict with 'success' bool and optional 'error'.
    """
    from services.student_service import get_student_by_roll
    from services.course_service import get_course_by_id

    # Validate student exists
    student = get_student_by_roll(roll_no)
    if not student:
        return {"success": False, "error": f"Student '{roll_no}' not found."}

    # Validate course exists
    course = get_course_by_id(course_id)
    if not course:
        return {"success": False, "error": f"Course '{course_id}' not found."}

    # Validate student is enrolled in the course
    if course_id not in student.get("enrolled_courses", []):
        return {
            "success": False,
            "error": "Student is not enrolled in this course.",
        }

    # Validate marks data
    if not marks_data:
        return {"success": False, "error": "No marks data provided."}

    course_subject_ids = {s["subject_id"] for s in course.get("subjects", [])}
    validated_marks = []
    for entry in marks_data:
        subject_id = entry.get("subject_id", "")
        if subject_id not in course_subject_ids:
            return {
                "success": False,
                "error": f"Subject '{subject_id}' does not belong to this course.",
            }
        try:
            marks_obtained = int(entry.get("marks_obtained", 0))
            max_marks = int(entry.get("max_marks", 100))
        except (ValueError, TypeError):
            return {"success": False, "error": "Marks must be valid integers."}

        if marks_obtained < 0 or max_marks <= 0 or marks_obtained > max_marks:
            return {
                "success": False,
                "error": f"Invalid marks for subject '{subject_id}'. "
                         f"Marks obtained ({marks_obtained}) must be between 0 and max marks ({max_marks}).",
            }
        validated_marks.append(
            {
                "subject_id": subject_id,
                "marks_obtained": marks_obtained,
                "max_marks": max_marks,
            }
        )

    all_marks = _read_marks()

    # Check if a record already exists; if so, update it (but keep published status)
    for record in all_marks:
        if record.get("roll_no") == roll_no and record.get("course_id") == course_id:
            record["marks"] = validated_marks
            # Do NOT reset published flag on update
            if _write_marks(all_marks):
                return {"success": True, "updated": True}
            return {"success": False, "error": "Failed to update marks."}

    # Create new record
    new_record: Dict[str, Any] = {
        "roll_no": roll_no,
        "course_id": course_id,
        "marks": validated_marks,
        "published": False,
        "is_published": False,
        "published_at": None,
    }
    all_marks.append(new_record)
    if _write_marks(all_marks):
        return {"success": True, "updated": False}
    return {"success": False, "error": "Failed to save marks."}


def publish_result(roll_no: str, course_id: str) -> Dict[str, Any]:
    """Publish the result for a student in a course.

    Args:
        roll_no: Student's roll number.
        course_id: Course ID.

    Returns:
        A dict with 'success' bool and optional 'error'.
    """
    all_marks = _read_marks()
    for record in all_marks:
        if record.get("roll_no") == roll_no and record.get("course_id") == course_id:
            if record.get("published"):
                return {"success": False, "error": "Result is already published."}
            record["published"] = True
            if _write_marks(all_marks):
                return {"success": True}
            return {"success": False, "error": "Failed to publish result."}

    return {
        "success": False,
        "error": "No marks record found for this student and course.",
    }


def unpublish_result(roll_no: str, course_id: str) -> Dict[str, Any]:
    """Unpublish the result for a student in a course.

    Args:
        roll_no: Student's roll number.
        course_id: Course ID.

    Returns:
        A dict with 'success' bool and optional 'error'.
    """
    all_marks = _read_marks()
    for record in all_marks:
        if record.get("roll_no") == roll_no and record.get("course_id") == course_id:
            record["published"] = False
            if _write_marks(all_marks):
                return {"success": True}
            return {"success": False, "error": "Failed to unpublish result."}

    return {
        "success": False,
        "error": "No marks record found for this student and course.",
    }


def get_student_results(roll_no: str) -> List[Dict[str, Any]]:
    """Return all marks records for a student (published or not)."""
    all_marks = _read_marks()
    return [r for r in all_marks if r.get("roll_no") == roll_no]


def get_published_result(roll_no: str, course_id: str) -> Optional[Dict[str, Any]]:
    """Return the published marks record for a student in a course, or None."""
    record = get_marks_record(roll_no, course_id)
    if record and record.get("published"):
        return record
    return None


def calculate_totals(record: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate total marks obtained and total max marks for a record.

    Args:
        record: A marks record dict.

    Returns:
        A dict with 'total_obtained', 'total_max', and 'percentage'.
    """
    marks_list = record.get("marks", [])
    total_obtained = sum(m.get("marks_obtained", 0) for m in marks_list)
    total_max = sum(m.get("max_marks", 0) for m in marks_list)
    percentage = round((total_obtained / total_max * 100), 2) if total_max > 0 else 0.0
    return {
        "total_obtained": total_obtained,
        "total_max": total_max,
        "percentage": percentage,
    }
