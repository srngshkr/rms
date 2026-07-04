/**
 * Result Management System — Main JavaScript
 * Handles client-side utilities: form validation, auto-dismiss alerts.
 */

'use strict';

// ---- Auto-dismiss flash alerts after 5 seconds ----
document.addEventListener('DOMContentLoaded', function () {
  const alerts = document.querySelectorAll('.alert.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 5000);
  });
});

// ---- Client-side form validation ----
document.addEventListener('DOMContentLoaded', function () {
  const forms = document.querySelectorAll('form[novalidate]');
  forms.forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add('was-validated');
    });
  });
});

// ---- Confirm before unpublishing a result ----
document.addEventListener('DOMContentLoaded', function () {
  const unpublishForms = document.querySelectorAll('form[action*="unpublish"]');
  unpublishForms.forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!confirm('Are you sure you want to unpublish this result? Students will no longer be able to view it.')) {
        event.preventDefault();
      }
    });
  });
});

// ---- Confirm before publishing a result ----
document.addEventListener('DOMContentLoaded', function () {
  const publishForms = document.querySelectorAll('form[action*="publish"]:not([action*="unpublish"])');
  publishForms.forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!confirm('Publish this result? Students will be able to view it immediately.')) {
        event.preventDefault();
      }
    });
  });
});

// =========================================================
// RMS Admin Dashboard — AJAX & UI Functions
// =========================================================

// ---- Toast Notification ----
function showToast(message, type) {
  const toastEl = document.getElementById('rms-toast');
  if (!toastEl) return;
  const toastBody = document.getElementById('rms-toast-body');
  toastEl.className = 'toast align-items-center border-0 text-white bg-' + (type || 'success');
  if (type === 'warning') toastEl.classList.add('text-dark');
  toastBody.textContent = message;
  const toast = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 4000 });
  toast.show();
}

// ---- Confirm Delete Dialog ----
let _deleteCallback = null;

function showConfirmDelete(message, callback) {
  const modalEl = document.getElementById('confirmDeleteModal');
  if (!modalEl) return;
  document.getElementById('confirm-delete-message').textContent = message;
  _deleteCallback = callback;
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
}

document.addEventListener('DOMContentLoaded', function () {
  const confirmBtn = document.getElementById('confirm-delete-btn');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', function () {
      const modalEl = document.getElementById('confirmDeleteModal');
      bootstrap.Modal.getOrCreateInstance(modalEl).hide();
      if (typeof _deleteCallback === 'function') {
        _deleteCallback();
        _deleteCallback = null;
      }
    });
  }
});

// =========================================================
// Student CRUD
// =========================================================

function openEditStudentModal(rollNo, name, phone, email, address, dob, enrolledCourses) {
  document.getElementById('edit-student-roll-no').value = rollNo;
  document.getElementById('edit-student-name').value = name;
  document.getElementById('edit-student-phone').value = phone;
  document.getElementById('edit-student-email').value = email;
  document.getElementById('edit-student-address').value = address;
  document.getElementById('edit-student-dob').value = dob;

  // Reset and set course checkboxes
  document.querySelectorAll('.edit-course-checkbox').forEach(function (cb) {
    cb.checked = enrolledCourses.includes(cb.value);
  });

  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('editStudentModal'));
  modal.show();
}

function submitEditStudent() {
  const rollNo = document.getElementById('edit-student-roll-no').value;
  const name = document.getElementById('edit-student-name').value.trim();
  const phone = document.getElementById('edit-student-phone').value.trim();
  const email = document.getElementById('edit-student-email').value.trim();
  const address = document.getElementById('edit-student-address').value.trim();
  const dob = document.getElementById('edit-student-dob').value.trim();
  const enrolledCourses = Array.from(
    document.querySelectorAll('.edit-course-checkbox:checked')
  ).map(cb => cb.value);

  if (!name || !phone || !email || !address || !dob) {
    showToast('All required fields must be filled.', 'danger');
    return;
  }

  fetch('/admin/students/' + encodeURIComponent(rollNo), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, phone, email, address, dob, enrolled_courses: enrolledCourses })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      bootstrap.Modal.getOrCreateInstance(document.getElementById('editStudentModal')).hide();
      showToast('Student updated successfully!', 'success');
      setTimeout(() => location.reload(), 1200);
    } else {
      showToast(data.message || 'Failed to update student.', 'danger');
    }
  })
  .catch(() => showToast('Network error. Please try again.', 'danger'));
}

function confirmDeleteStudent(rollNo, name) {
  showConfirmDelete(
    'Are you sure you want to delete student "' + name + '" (Roll No: ' + rollNo + ')? This action cannot be undone.',
    function () { deleteStudent(rollNo); }
  );
}

function deleteStudent(rollNo) {
  fetch('/admin/students/' + encodeURIComponent(rollNo), { method: 'DELETE' })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      showToast('Student deleted successfully.', 'success');
      const row = document.getElementById('student-row-' + rollNo);
      if (row) row.remove();
    } else {
      showToast(data.message || 'Failed to delete student.', 'danger');
    }
  })
  .catch(() => showToast('Network error. Please try again.', 'danger'));
}

// =========================================================
// Course CRUD
// =========================================================

function openEditCourseModal(courseId, courseName, code, description, subjects) {
  document.getElementById('edit-course-id').value = courseId;
  document.getElementById('edit-course-name').value = courseName;
  document.getElementById('edit-course-code').value = code || '';
  document.getElementById('edit-course-description').value = description || '';
  // Populate subjects as comma-separated names
  const subjectNames = (subjects || []).map(s => (typeof s === 'object' ? s.subject_name : s)).join(', ');
  document.getElementById('edit-course-subjects').value = subjectNames;

  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('editCourseModal'));
  modal.show();
}

function submitEditCourse() {
  const courseId = document.getElementById('edit-course-id').value;
  const courseName = document.getElementById('edit-course-name').value.trim();
  const code = document.getElementById('edit-course-code').value.trim();
  const description = document.getElementById('edit-course-description').value.trim();
  const subjectsRaw = document.getElementById('edit-course-subjects').value.trim();
  const subjects = subjectsRaw.split(',').map(s => s.trim()).filter(s => s);

  if (!courseName) {
    showToast('Course name is required.', 'danger');
    return;
  }

  fetch('/admin/courses/' + encodeURIComponent(courseId), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ course_name: courseName, code, description, subjects })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      bootstrap.Modal.getOrCreateInstance(document.getElementById('editCourseModal')).hide();
      showToast('Course updated successfully!', 'success');
      setTimeout(() => location.reload(), 1200);
    } else {
      showToast(data.message || 'Failed to update course.', 'danger');
    }
  })
  .catch(() => showToast('Network error. Please try again.', 'danger'));
}

function confirmDeleteCourse(courseId, courseName) {
  showConfirmDelete(
    'Are you sure you want to delete course "' + courseName + '"? This will fail if active students are enrolled.',
    function () { deleteCourse(courseId); }
  );
}

function deleteCourse(courseId) {
  fetch('/admin/courses/' + encodeURIComponent(courseId), { method: 'DELETE' })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      showToast('Course deleted successfully.', 'success');
      const row = document.getElementById('course-row-' + courseId);
      if (row) row.remove();
    } else {
      showToast(data.message || 'Failed to delete course.', 'danger');
    }
  })
  .catch(() => showToast('Network error. Please try again.', 'danger'));
}

// =========================================================
// Publish Results
// =========================================================

document.addEventListener('DOMContentLoaded', function () {
  const publishSelect = document.getElementById('publish-course-select');
  if (publishSelect) {
    publishSelect.addEventListener('change', function () {
      const hasValue = !!this.value;
      document.getElementById('btn-publish').disabled = !hasValue;
      document.getElementById('btn-unpublish').disabled = !hasValue;
      document.getElementById('btn-load-results').disabled = !hasValue;
      // Clear results area when course changes
      document.getElementById('publish-results-area').classList.add('d-none');
      document.getElementById('publish-empty-state').classList.remove('d-none');
    });
  }
});

function loadCourseResults() {
  const courseId = document.getElementById('publish-course-select').value;
  if (!courseId) return;

  fetch('/admin/results/course/' + encodeURIComponent(courseId))
  .then(res => res.json())
  .then(data => {
    if (!data.success) {
      showToast(data.message || 'Failed to load results.', 'danger');
      return;
    }
    renderPublishResults(data.data);
  })
  .catch(() => showToast('Network error. Please try again.', 'danger'));
}

function renderPublishResults(data) {
  const results = data.results || [];
  const course = data.course || {};
  const isPublished = data.is_published || false;

  document.getElementById('publish-course-name').textContent = course.course_name || 'Course Results';
  const statusBadge = document.getElementById('publish-status-badge');
  statusBadge.innerHTML = isPublished
    ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Published</span>'
    : '<span class="badge bg-secondary"><i class="bi bi-hourglass-split me-1"></i>Not Published</span>';

  const tbody = document.getElementById('publish-results-tbody');
  tbody.innerHTML = '';

  if (results.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-3">No marks records found for this course.</td></tr>';
  } else {
    results.forEach(r => {
      const resultClass = r.overall_result === 'Pass' ? 'bg-success' : 'bg-danger';
      const pubClass = r.is_published ? 'bg-success' : 'bg-secondary';
      tbody.innerHTML += `
        <tr>
          <td><span class="badge bg-primary">${r.roll_no}</span></td>
          <td class="fw-semibold">${r.student_name}</td>
          <td>${(r.marks || []).length}</td>
          <td class="text-center">${r.total_obtained} / ${r.total_max}</td>
          <td class="text-center">${r.overall_percentage}%</td>
          <td class="text-center"><span class="badge bg-info text-dark">${r.overall_grade}</span></td>
          <td class="text-center"><span class="badge ${resultClass}">${r.overall_result}</span></td>
          <td class="text-center"><span class="badge ${pubClass}">${r.is_published ? 'Yes' : 'No'}</span></td>
        </tr>`;
    });
  }

  document.getElementById('publish-empty-state').classList.add('d-none');
  document.getElementById('publish-results-area').classList.remove('d-none');
}

function publishResults() {
  const courseId = document.getElementById('publish-course-select').value;
  if (!courseId) return;

  if (!confirm('Publish all results for this course? Students will be able to view them immediately.')) return;

  fetch('/admin/results/publish/' + encodeURIComponent(courseId), { method: 'POST' })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      showToast(data.message || 'Results published!', 'success');
      loadCourseResults();
    } else {
      showToast(data.message || 'Failed to publish results.', 'danger');
    }
  })
  .catch(() => showToast('Network error. Please try again.', 'danger'));
}

function unpublishResults() {
  const courseId = document.getElementById('publish-course-select').value;
  if (!courseId) return;

  if (!confirm('Unpublish all results for this course? Students will no longer be able to view them.')) return;

  fetch('/admin/results/unpublish/' + encodeURIComponent(courseId), { method: 'POST' })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      showToast(data.message || 'Results unpublished.', 'warning');
      loadCourseResults();
    } else {
      showToast(data.message || 'Failed to unpublish results.', 'danger');
    }
  })
  .catch(() => showToast('Network error. Please try again.', 'danger'));
}
