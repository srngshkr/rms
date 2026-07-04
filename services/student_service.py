"""Student service for managing student onboarding and enrollment using JSON file storage."""

import json
import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


def _get_students_file() -> str:
    """Get the path to the students JSON file."""
    from config import Config
    return Config.STUDENTS_FILE


def _read_students() -> List[Dict[str, Any]]:
    """Read all students from the JSON file."""
    file_path = _get_students_file()
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Error reading students file: %s", e)
        return []


def _write_students(students: List[Dict[str, Any]]) -> bool:
    """Write students list to the JSON file."""
    file_path = _get_students_file()
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(students, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        logger.error("Error writing students file: %s", e)
        return False


def _generate_roll_no(students: List[Dict[str, Any]]) -> str:
    """Generate the next sequential roll number prefixed with the current year.

    Format: YYYY + 3-digit sequential number, e.g. 2026001
    """
    current_year = str(datetime.now().year)
    max_seq = 0
    for student in students:
        roll = student.get("roll_no", "")
        if roll.startswith(current_year) and len(roll) > len(current_year):
            try:
                seq = int(roll[len(current_year):])
                if seq > max_seq:
                    max_seq = seq
            except ValueError:
                pass
    return f"{current_year}{max_seq + 1:03d}"


def get_all_students() -> List[Dict[str, Any]]:
    """Return a list of all students."""
    return _read_students()


def get_student_by_roll(roll_no: str) -> Optional[Dict[str, Any]]:
    """Return a student by roll number, or None if not found."""
    students = _read_students()
    for student in students:
        if student.get("roll_no") == roll_no:
            return student
    return None


def is_duplicate(phone: str, email: str) -> bool:
    """Check if a student with the same phone AND email already exists."""
    students = _read_students()
    phone = phone.strip().lower()
    email = email.strip().lower()
    return any(
        s.get("phone", "").strip().lower() == phone
        and s.get("email", "").strip().lower() == email
        for s in students
    )


def add_student(
    name: str,
    phone: str,
    email: str,
    address: str,
    dob: str,
    enrolled_courses: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Onboard a new student.

    Args:
        name: Full name of the student.
        phone: Phone number.
        email: Email address.
        address: Residential address.
        dob: Date of birth in YYYY-MM-DD format.
        enrolled_courses: List of course IDs to enroll the student in.

    Returns:
        A dict with 'success' bool and either 'student' or 'error'.
    """
    # Validate required fields
    name = name.strip()
    phone = phone.strip()
    email = email.strip()
    address = address.strip()
    dob = dob.strip()

    if not all([name, phone, email, address, dob]):
        return {"success": False, "error": "All fields are required."}

    # Validate email format (basic)
    if "@" not in email or "." not in email:
        return {"success": False, "error": "Invalid email address."}

    # Validate phone (digits only, 7-15 chars)
    if not phone.isdigit() or not (7 <= len(phone) <= 15):
        return {"success": False, "error": "Phone number must be 7-15 digits."}

    # Validate date of birth
    try:
        datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        return {"success": False, "error": "Date of birth must be in YYYY-MM-DD format."}

    # Uniqueness check: phone + email combo
    if is_duplicate(phone, email):
        return {
            "success": False,
            "error": "A student with the same phone and email already exists.",
        }

    students = _read_students()
    roll_no = _generate_roll_no(students)

    new_student: Dict[str, Any] = {
        "roll_no": roll_no,
        "name": name,
        "phone": phone,
        "email": email.lower(),
        "address": address,
        "dob": dob,
        "enrolled_courses": enrolled_courses if enrolled_courses else [],
    }

    students.append(new_student)
    if _write_students(students):
        return {"success": True, "student": new_student}
    return {"success": False, "error": "Failed to save student. Please try again."}


def enroll_student_in_course(roll_no: str, course_id: str) -> Dict[str, Any]:
    """Enroll an existing student in a course.

    Args:
        roll_no: The student's roll number.
        course_id: The course ID to enroll in.

    Returns:
        A dict with 'success' bool and optional 'error'.
    """
    students = _read_students()
    for student in students:
        if student.get("roll_no") == roll_no:
            enrolled = student.setdefault("enrolled_courses", [])
            if course_id in enrolled:
                return {
                    "success": False,
                    "error": "Student is already enrolled in this course.",
                }
            enrolled.append(course_id)
            if _write_students(students):
                return {"success": True}
            return {"success": False, "error": "Failed to update enrollment."}

    return {"success": False, "error": f"Student '{roll_no}' not found."}


def get_students_by_course(course_id: str) -> List[Dict[str, Any]]:
    """Return all students enrolled in a specific course."""
    students = _read_students()
    return [
        s for s in students if course_id in s.get("enrolled_courses", [])
    ]


def get_student_by_roll_no(roll_no: str) -> Optional[Dict[str, Any]]:
    """Return a student by roll number, or None if not found.

    Args:
        roll_no: The student's roll number.

    Returns:
        The student dict or None if not found.
    """
    return get_student_by_roll(roll_no)


def update_student(roll_no: str, updated_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing student's information.

    Validates unique phone+email combo excluding the current student.

    Args:
        roll_no: The student's roll number.
        updated_data: Dict with fields to update (name, phone, email, address, dob, enrolled_courses).

    Returns:
        A dict with 'success' bool and either 'student' or 'error'.
    """
    students = _read_students()
    target_index = None
    for i, student in enumerate(students):
        if student.get("roll_no") == roll_no:
            target_index = i
            break

    if target_index is None:
        return {"success": False, "error": f"Student '{roll_no}' not found."}

    current_student = students[target_index]

    # Extract and validate fields
    name = updated_data.get("name", current_student.get("name", "")).strip()
    phone = updated_data.get("phone", current_student.get("phone", "")).strip()
    email = updated_data.get("email", current_student.get("email", "")).strip()
    address = updated_data.get("address", current_student.get("address", "")).strip()
    dob = updated_data.get("dob", current_student.get("dob", "")).strip()
    enrolled_courses = updated_data.get("enrolled_courses", current_student.get("enrolled_courses", []))

    if not all([name, phone, email, address, dob]):
        return {"success": False, "error": "All fields are required."}

    # Validate email format
    if "@" not in email or "." not in email:
        return {"success": False, "error": "Invalid email address."}

    # Validate phone
    if not phone.isdigit() or not (7 <= len(phone) <= 15):
        return {"success": False, "error": "Phone number must be 7-15 digits."}

    # Validate date of birth
    try:
        datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        return {"success": False, "error": "Date of birth must be in YYYY-MM-DD format."}

    # Check uniqueness: phone + email combo (excluding current student)
    phone_lower = phone.strip().lower()
    email_lower = email.strip().lower()
    for i, s in enumerate(students):
        if i == target_index:
            continue
        if (
            s.get("phone", "").strip().lower() == phone_lower
            and s.get("email", "").strip().lower() == email_lower
        ):
            return {
                "success": False,
                "error": "Another student with the same phone and email already exists.",
            }

    # Apply updates
    students[target_index] = {
        **current_student,
        "name": name,
        "phone": phone,
        "email": email.lower(),
        "address": address,
        "dob": dob,
        "enrolled_courses": enrolled_courses,
    }

    if _write_students(students):
        return {"success": True, "student": students[target_index]}
    return {"success": False, "error": "Failed to update student. Please try again."}


def delete_student(roll_no: str) -> Dict[str, Any]:
    """Soft-delete a student by marking them as inactive.

    Args:
        roll_no: The student's roll number.

    Returns:
        A dict with 'success' bool and optional 'error'.
    """
    students = _read_students()
    for student in students:
        if student.get("roll_no") == roll_no:
            if not student.get("is_active", True):
                return {"success": False, "error": "Student is already inactive."}
            student["is_active"] = False
            if _write_students(students):
                return {"success": True}
            return {"success": False, "error": "Failed to delete student. Please try again."}

    return {"success": False, "error": f"Student '{roll_no}' not found."}
