"""Result service for managing result publication and student result retrieval."""

import json
import os
import logging
from datetime import datetime, timezone
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


def _calculate_grade(percentage: float) -> str:
    """Calculate grade based on percentage.

    Args:
        percentage: The percentage score (0-100).

    Returns:
        Grade letter: A, B, C, D, or F.
    """
    if percentage >= 90:
        return "A"
    elif percentage >= 80:
        return "B"
    elif percentage >= 70:
        return "C"
    elif percentage >= 60:
        return "D"
    else:
        return "F"


def _enrich_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich a marks record with grade, pass/fail status, and totals.

    Args:
        record: A marks record dict.

    Returns:
        Enriched record with additional computed fields.
    """
    from services.course_service import get_course_by_id
    from services.student_service import get_student_by_roll

    course_id = record.get("course_id", "")
    roll_no = record.get("roll_no", "")

    course = get_course_by_id(course_id) or {}
    student = get_student_by_roll(roll_no) or {}

    subject_map = {
        s["subject_id"]: s["subject_name"]
        for s in course.get("subjects", [])
    }

    marks_list = record.get("marks", [])
    total_obtained = 0
    total_max = 0
    enriched_marks = []
    all_passed = True

    for m in marks_list:
        obtained = m.get("marks_obtained", 0)
        max_m = m.get("max_marks", 100)
        total_obtained += obtained
        total_max += max_m
        pct = round((obtained / max_m * 100), 2) if max_m > 0 else 0.0
        grade = _calculate_grade(pct)
        passed = pct >= 40
        if not passed:
            all_passed = False
        enriched_marks.append({
            "subject_id": m.get("subject_id", ""),
            "subject_name": subject_map.get(m.get("subject_id", ""), m.get("subject_id", "")),
            "marks_obtained": obtained,
            "max_marks": max_m,
            "percentage": pct,
            "grade": grade,
            "status": "Pass" if passed else "Fail",
        })

    overall_pct = round((total_obtained / total_max * 100), 2) if total_max > 0 else 0.0
    overall_grade = _calculate_grade(overall_pct)
    overall_result = "Pass" if all_passed and overall_pct >= 40 else "Fail"

    return {
        "roll_no": roll_no,
        "course_id": course_id,
        "course_name": course.get("course_name", course_id),
        "student_name": student.get("name", roll_no),
        "marks": enriched_marks,
        "total_obtained": total_obtained,
        "total_max": total_max,
        "overall_percentage": overall_pct,
        "overall_grade": overall_grade,
        "overall_result": overall_result,
        "is_published": record.get("is_published", record.get("published", False)),
        "published_at": record.get("published_at", None),
    }


def publish_results(course_id: str) -> Dict[str, Any]:
    """Publish all results for a course.

    Sets is_published=True and published_at=timestamp for all marks records
    of the given course.

    Args:
        course_id: The course ID to publish results for.

    Returns:
        A dict with 'success' bool and optional 'error' or 'count'.
    """
    all_marks = _read_marks()
    updated_count = 0
    timestamp = datetime.now(timezone.utc).isoformat()

    for record in all_marks:
        if record.get("course_id") == course_id:
            record["is_published"] = True
            record["published"] = True  # backward compatibility
            record["published_at"] = timestamp
            updated_count += 1

    if updated_count == 0:
        return {"success": False, "error": "No marks records found for this course."}

    if _write_marks(all_marks):
        return {"success": True, "count": updated_count}
    return {"success": False, "error": "Failed to publish results."}


def unpublish_results(course_id: str) -> Dict[str, Any]:
    """Unpublish all results for a course.

    Sets is_published=False for all marks records of the given course.

    Args:
        course_id: The course ID to unpublish results for.

    Returns:
        A dict with 'success' bool and optional 'error' or 'count'.
    """
    all_marks = _read_marks()
    updated_count = 0

    for record in all_marks:
        if record.get("course_id") == course_id:
            record["is_published"] = False
            record["published"] = False  # backward compatibility
            updated_count += 1

    if updated_count == 0:
        return {"success": False, "error": "No marks records found for this course."}

    if _write_marks(all_marks):
        return {"success": True, "count": updated_count}
    return {"success": False, "error": "Failed to unpublish results."}


def get_results_by_roll_no(
    roll_no: str, course_id: str
) -> Dict[str, Any]:
    """Fetch published results for a student by roll number and course.

    Returns results only if is_published=True.

    Args:
        roll_no: The student's roll number.
        course_id: The course ID.

    Returns:
        A dict with 'success' bool and either 'result' or 'error'.
    """
    all_marks = _read_marks()
    for record in all_marks:
        if record.get("roll_no") == roll_no and record.get("course_id") == course_id:
            is_published = record.get("is_published", record.get("published", False))
            if not is_published:
                return {
                    "success": False,
                    "error": "Results are not yet published for this course.",
                }
            return {"success": True, "result": _enrich_record(record)}

    return {"success": False, "error": "No record found for this student and course."}


def get_all_results_for_student(
    roll_no: str, admin: bool = False
) -> Dict[str, Any]:
    """Get all results for a student across all courses.

    Args:
        roll_no: The student's roll number.
        admin: If True, return all results. If False, return only published results.

    Returns:
        A dict with 'success' bool and either 'results' list or 'error'.
    """
    from services.student_service import get_student_by_roll

    student = get_student_by_roll(roll_no)
    if not student:
        return {"success": False, "error": f"Student '{roll_no}' not found."}

    all_marks = _read_marks()
    results = []
    for record in all_marks:
        if record.get("roll_no") == roll_no:
            is_published = record.get("is_published", record.get("published", False))
            if admin or is_published:
                results.append(_enrich_record(record))

    return {
        "success": True,
        "student": student,
        "results": results,
    }


def get_course_results_for_publish(course_id: str) -> Dict[str, Any]:
    """Get all student results for a course (for admin review before publishing).

    Args:
        course_id: The course ID.

    Returns:
        A dict with 'success' bool and either 'results' list or 'error'.
    """
    from services.course_service import get_course_by_id

    course = get_course_by_id(course_id)
    if not course:
        return {"success": False, "error": f"Course '{course_id}' not found."}

    all_marks = _read_marks()
    results = []
    for record in all_marks:
        if record.get("course_id") == course_id:
            results.append(_enrich_record(record))

    return {
        "success": True,
        "course": course,
        "results": results,
        "is_published": any(
            r.get("is_published", False) for r in results
        ) if results else False,
    }
