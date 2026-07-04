"""Student-facing routes: home page and result lookup views."""

import logging
from flask import Blueprint, flash, jsonify, render_template, request

from services import course_service, student_service, marks_service, result_service

logger = logging.getLogger(__name__)

student_bp = Blueprint("student", __name__)


@student_bp.route("/", methods=["GET", "POST"])
def home():
    """Home page with two sections:
    - Section 1: Enter Roll No to view all enrolled courses and their result status.
    - Section 2: Enter Roll No + Course to view detailed result (only if published).
    """
    # --- Section 1: Course enrollment overview ---
    section1_data = None
    section1_roll = ""

    # --- Section 2: Detailed result view ---
    section2_data = None
    section2_roll = ""
    section2_course_id = ""
    section2_error = None

    all_courses = course_service.get_all_courses()
    course_map = {c["course_id"]: c for c in all_courses}

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "lookup_courses":
            # Section 1 submission
            roll_no = request.form.get("roll_no_1", "").strip()
            section1_roll = roll_no
            student = student_service.get_student_by_roll(roll_no)
            if not student:
                flash("No student found with this Roll Number.", "warning")
            else:
                enrolled_course_ids = student.get("enrolled_courses", [])
                courses_info = []
                for cid in enrolled_course_ids:
                    course = course_map.get(cid)
                    if not course:
                        continue
                    marks_record = marks_service.get_marks_record(roll_no, cid)
                    status = "Not Submitted"
                    if marks_record:
                        status = "Published" if marks_record.get("published") else "Pending"
                    courses_info.append(
                        {
                            "course_id": cid,
                            "course_name": course["course_name"],
                            "status": status,
                        }
                    )
                section1_data = {
                    "student": student,
                    "courses": courses_info,
                }

        elif action == "view_result":
            # Section 2 submission
            roll_no = request.form.get("roll_no_2", "").strip()
            course_id = request.form.get("course_id_2", "").strip()
            section2_roll = roll_no
            section2_course_id = course_id

            student = student_service.get_student_by_roll(roll_no)
            if not student:
                section2_error = "No student found with this Roll Number."
            elif course_id not in student.get("enrolled_courses", []):
                section2_error = "This student is not enrolled in the selected course."
            else:
                record = marks_service.get_published_result(roll_no, course_id)
                if not record:
                    section2_error = (
                        "Result is not yet published for this course, "
                        "or no marks have been submitted."
                    )
                else:
                    course = course_map.get(course_id, {})
                    # Enrich marks with subject names
                    subject_map = {
                        s["subject_id"]: s["subject_name"]
                        for s in course.get("subjects", [])
                    }
                    enriched_marks = [
                        {
                            "subject_name": subject_map.get(
                                m["subject_id"], m["subject_id"]
                            ),
                            "marks_obtained": m["marks_obtained"],
                            "max_marks": m["max_marks"],
                        }
                        for m in record.get("marks", [])
                    ]
                    totals = marks_service.calculate_totals(record)
                    section2_data = {
                        "student": student,
                        "course": course,
                        "marks": enriched_marks,
                        "totals": totals,
                    }

    return render_template(
        "student/home.html",
        courses=all_courses,
        section1_data=section1_data,
        section1_roll=section1_roll,
        section2_data=section2_data,
        section2_roll=section2_roll,
        section2_course_id=section2_course_id,
        section2_error=section2_error,
    )


@student_bp.route("/results/<roll_no>", methods=["GET"])
def get_student_results(roll_no: str):
    """API endpoint: get all published results for a student by roll number.

    Returns only published results unless the requester is an admin.
    """
    from flask import session
    is_admin = session.get("admin_logged_in", False)
    result = result_service.get_all_results_for_student(roll_no, admin=is_admin)
    if result["success"]:
        return jsonify({"success": True, "data": result})
    return jsonify({"success": False, "message": result["error"]}), 404


@student_bp.route("/result-lookup", methods=["GET"])
def result_lookup_page():
    """Roll number lookup page for students to check results."""
    all_courses = course_service.get_all_courses()
    return render_template("student/result_lookup.html", courses=all_courses)


@student_bp.route("/result-lookup", methods=["POST"])
def result_lookup():
    """Process roll number lookup: course_id + roll_no, return published results only."""
    data = request.get_json(force=True, silent=True) or {}
    roll_no = data.get("roll_no", "").strip()
    course_id = data.get("course_id", "").strip()

    if not roll_no or not course_id:
        return jsonify({"success": False, "message": "Roll number and course are required."}), 400

    result = result_service.get_results_by_roll_no(roll_no, course_id)
    if result["success"]:
        return jsonify({"success": True, "data": result["result"]})
    return jsonify({"success": False, "message": result["error"]}), 404
