"""Admin routes for managing courses, students, marks, and result publication."""

import logging
from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from routes.auth import login_required
from services import course_service, student_service, marks_service, result_service

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@admin_bp.route("/")
@login_required
def dashboard():
    """Admin dashboard showing summary counts."""
    courses = course_service.get_all_courses()
    students = student_service.get_all_students()
    all_marks = marks_service.get_all_marks()
    published_count = sum(1 for m in all_marks if m.get("published"))
    return render_template(
        "admin/dashboard.html",
        courses=courses,
        students=students,
        marks=all_marks,
        published_count=published_count,
    )


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

@admin_bp.route("/courses", methods=["GET", "POST"])
@login_required
def courses():
    """List all courses and handle new course creation."""
    if request.method == "POST":
        course_name = request.form.get("course_name", "").strip()
        # Collect all subject names from dynamic fields
        subjects = request.form.getlist("subjects")
        subjects = [s.strip() for s in subjects if s.strip()]

        result = course_service.add_course(course_name, subjects)
        if result["success"]:
            flash(
                f"Course '{result['course']['course_name']}' added successfully!",
                "success",
            )
            return redirect(url_for("admin.courses"))
        else:
            flash(result["error"], "danger")

    all_courses = course_service.get_all_courses()
    return render_template("admin/course_form.html", courses=all_courses)


@admin_bp.route("/courses/<course_id>/subjects", methods=["GET", "POST"])
@login_required
def add_subject(course_id: str):
    """Add a new subject to an existing course."""
    course = course_service.get_course_by_id(course_id)
    if not course:
        flash(f"Course '{course_id}' not found.", "danger")
        return redirect(url_for("admin.courses"))

    if request.method == "POST":
        subject_name = request.form.get("subject_name", "").strip()
        result = course_service.add_subject_to_course(course_id, subject_name)
        if result["success"]:
            flash(
                f"Subject '{result['subject']['subject_name']}' added successfully!",
                "success",
            )
            return redirect(url_for("admin.courses"))
        else:
            flash(result["error"], "danger")

    return render_template("admin/add_subject.html", course=course)


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------

@admin_bp.route("/students", methods=["GET", "POST"])
@login_required
def students():
    """List all students and handle new student onboarding."""
    all_courses = course_service.get_all_courses()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        dob = request.form.get("dob", "").strip()
        enrolled_courses = request.form.getlist("enrolled_courses")

        result = student_service.add_student(
            name=name,
            phone=phone,
            email=email,
            address=address,
            dob=dob,
            enrolled_courses=enrolled_courses,
        )
        if result["success"]:
            student = result["student"]
            flash(
                f"Student '{student['name']}' onboarded successfully! "
                f"Roll No: {student['roll_no']}",
                "success",
            )
            return redirect(url_for("admin.students"))
        else:
            flash(result["error"], "danger")

    all_students = student_service.get_all_students()
    # Enrich students with course names
    course_map = {c["course_id"]: c["course_name"] for c in all_courses}
    return render_template(
        "admin/student_form.html",
        students=all_students,
        courses=all_courses,
        course_map=course_map,
    )


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

@admin_bp.route("/marks", methods=["GET", "POST"])
@login_required
def marks():
    """Submit marks for a student in a course."""
    all_courses = course_service.get_all_courses()
    all_students = student_service.get_all_students()
    all_marks = marks_service.get_all_marks()

    if request.method == "POST":
        roll_no = request.form.get("roll_no", "").strip()
        course_id = request.form.get("course_id", "").strip()

        # Get the course to know its subjects
        course = course_service.get_course_by_id(course_id)
        if not course:
            flash("Selected course not found.", "danger")
            return redirect(url_for("admin.marks"))

        # Build marks_data from form
        marks_data = []
        for subject in course.get("subjects", []):
            sid = subject["subject_id"]
            marks_obtained_str = request.form.get(f"marks_{sid}", "0").strip()
            max_marks_str = request.form.get(f"max_{sid}", "100").strip()
            try:
                marks_obtained = int(marks_obtained_str)
                max_marks = int(max_marks_str)
            except ValueError:
                flash(
                    f"Invalid marks value for subject '{subject['subject_name']}'.",
                    "danger",
                )
                return redirect(url_for("admin.marks"))
            marks_data.append(
                {
                    "subject_id": sid,
                    "marks_obtained": marks_obtained,
                    "max_marks": max_marks,
                }
            )

        result = marks_service.submit_marks(roll_no, course_id, marks_data)
        if result["success"]:
            action = "updated" if result.get("updated") else "submitted"
            flash(f"Marks {action} successfully!", "success")
            return redirect(url_for("admin.marks"))
        else:
            flash(result["error"], "danger")

    # Enrich marks with student names and course names
    course_map = {c["course_id"]: c["course_name"] for c in all_courses}
    student_map = {s["roll_no"]: s["name"] for s in all_students}

    return render_template(
        "admin/marks_form.html",
        courses=all_courses,
        students=all_students,
        marks=all_marks,
        course_map=course_map,
        student_map=student_map,
    )


@admin_bp.route("/marks/publish", methods=["POST"])
@login_required
def publish_result():
    """Publish a result for a student-course combination."""
    roll_no = request.form.get("roll_no", "").strip()
    course_id = request.form.get("course_id", "").strip()

    result = marks_service.publish_result(roll_no, course_id)
    if result["success"]:
        flash(
            f"Result for Roll No '{roll_no}' in course '{course_id}' published!",
            "success",
        )
    else:
        flash(result["error"], "danger")

    return redirect(url_for("admin.marks"))


@admin_bp.route("/marks/unpublish", methods=["POST"])
@login_required
def unpublish_result():
    """Unpublish a result for a student-course combination."""
    roll_no = request.form.get("roll_no", "").strip()
    course_id = request.form.get("course_id", "").strip()

    result = marks_service.unpublish_result(roll_no, course_id)
    if result["success"]:
        flash(
            f"Result for Roll No '{roll_no}' in course '{course_id}' unpublished.",
            "info",
        )
    else:
        flash(result["error"], "danger")

    return redirect(url_for("admin.marks"))


@admin_bp.route("/marks/get_subjects")
@login_required
def get_subjects():
    """AJAX endpoint: return subjects for a given course_id as JSON."""
    course_id = request.args.get("course_id", "").strip()
    course = course_service.get_course_by_id(course_id)
    if not course:
        return jsonify({"subjects": []})
    return jsonify({"subjects": course.get("subjects", [])})


@admin_bp.route("/marks/get_enrolled_students")
@login_required
def get_enrolled_students():
    """AJAX endpoint: return students enrolled in a given course_id as JSON."""
    course_id = request.args.get("course_id", "").strip()
    enrolled = student_service.get_students_by_course(course_id)
    return jsonify(
        {
            "students": [
                {"roll_no": s["roll_no"], "name": s["name"]} for s in enrolled
            ]
        }
    )


# ---------------------------------------------------------------------------
# Student API Routes (JSON)
# ---------------------------------------------------------------------------

@admin_bp.route("/students", methods=["GET"])
@login_required
def list_students_api():
    """API endpoint: return all students as JSON."""
    all_students = student_service.get_all_students()
    all_courses = course_service.get_all_courses()
    course_map = {c["course_id"]: c["course_name"] for c in all_courses}
    students_with_courses = []
    for s in all_students:
        enrolled_names = [
            course_map.get(cid, cid) for cid in s.get("enrolled_courses", [])
        ]
        students_with_courses.append({**s, "enrolled_course_names": enrolled_names})
    return jsonify({"success": True, "data": students_with_courses})


@admin_bp.route("/students/<roll_no>", methods=["PUT"])
@login_required
def update_student_api(roll_no: str):
    """API endpoint: update a student by roll number."""
    data = request.get_json(force=True, silent=True) or {}
    result = student_service.update_student(roll_no, data)
    if result["success"]:
        return jsonify({"success": True, "message": "Student updated successfully.", "data": result["student"]})
    return jsonify({"success": False, "message": result["error"]}), 400


@admin_bp.route("/students/<roll_no>", methods=["DELETE"])
@login_required
def delete_student_api(roll_no: str):
    """API endpoint: soft-delete a student by roll number."""
    result = student_service.delete_student(roll_no)
    if result["success"]:
        return jsonify({"success": True, "message": "Student deleted successfully."})
    return jsonify({"success": False, "message": result["error"]}), 400


# ---------------------------------------------------------------------------
# Course API Routes (JSON)
# ---------------------------------------------------------------------------

@admin_bp.route("/courses", methods=["GET"])
@login_required
def list_courses_api():
    """API endpoint: return all courses as JSON."""
    all_courses = course_service.get_all_courses()
    return jsonify({"success": True, "data": all_courses})


@admin_bp.route("/courses/<course_id>", methods=["PUT"])
@login_required
def update_course_api(course_id: str):
    """API endpoint: update a course by course_id."""
    data = request.get_json(force=True, silent=True) or {}
    result = course_service.update_course(course_id, data)
    if result["success"]:
        return jsonify({"success": True, "message": "Course updated successfully.", "data": result["course"]})
    return jsonify({"success": False, "message": result["error"]}), 400


@admin_bp.route("/courses/<course_id>", methods=["DELETE"])
@login_required
def delete_course_api(course_id: str):
    """API endpoint: soft-delete a course by course_id."""
    result = course_service.delete_course(course_id)
    if result["success"]:
        return jsonify({"success": True, "message": "Course deleted successfully."})
    return jsonify({"success": False, "message": result["error"]}), 400


# ---------------------------------------------------------------------------
# Result Publishing API Routes (JSON)
# ---------------------------------------------------------------------------

@admin_bp.route("/results/course/<course_id>", methods=["GET"])
@login_required
def get_course_results_api(course_id: str):
    """API endpoint: get all results for a course (for admin review)."""
    result = result_service.get_course_results_for_publish(course_id)
    if result["success"]:
        return jsonify({"success": True, "data": result})
    return jsonify({"success": False, "message": result["error"]}), 404


@admin_bp.route("/results/publish/<course_id>", methods=["POST"])
@login_required
def publish_course_results_api(course_id: str):
    """API endpoint: publish all results for a course."""
    result = result_service.publish_results(course_id)
    if result["success"]:
        return jsonify({
            "success": True,
            "message": f"Results published for {result['count']} student(s).",
            "count": result["count"],
        })
    return jsonify({"success": False, "message": result["error"]}), 400


@admin_bp.route("/results/unpublish/<course_id>", methods=["POST"])
@login_required
def unpublish_course_results_api(course_id: str):
    """API endpoint: unpublish all results for a course."""
    result = result_service.unpublish_results(course_id)
    if result["success"]:
        return jsonify({
            "success": True,
            "message": f"Results unpublished for {result['count']} student(s).",
            "count": result["count"],
        })
    return jsonify({"success": False, "message": result["error"]}), 400
