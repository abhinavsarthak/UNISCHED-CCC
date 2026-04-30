"""
app.py – University Course Scheduling System
Flask + MySQL + Greedy / Backtracking algorithms
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import database as db
from algorithms import greedy_schedule, backtracking_schedule, hybrid_schedule
import datetime
from flask.json.provider import DefaultJSONProvider

class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.time, datetime.datetime)):
            return obj.isoformat()
        if isinstance(obj, datetime.timedelta):
            return str(obj)
        return super().default(obj)

app = Flask(__name__)
app.json_provider_class = CustomJSONProvider
app.json = CustomJSONProvider(app)
app.secret_key = "ucs-secret-2025"



def _get_blocked() -> dict[int, set]:
    rows = db.fetchall(
        "SELECT instructor_id, time_slot_id FROM instructor_unavailability"
    )
    blocked: dict[int, set] = {}
    for r in rows:
        blocked.setdefault(r["instructor_id"], set()).add(r["time_slot_id"])
    return blocked


def _clear_schedule(semester: str, year: int) -> None:
    db.execute(
        "DELETE FROM schedules WHERE semester=%s AND year=%s", (semester, year)
    )
    db.execute(
        "DELETE FROM conflict_log WHERE semester=%s AND year=%s", (semester, year)
    )




@app.route("/")
def index():
    stats = {
        "courses":     db.fetchone("SELECT COUNT(*) AS n FROM courses")["n"],
        "classrooms":  db.fetchone("SELECT COUNT(*) AS n FROM classrooms")["n"],
        "instructors": db.fetchone("SELECT COUNT(*) AS n FROM instructors")["n"],
        "time_slots":  db.fetchone("SELECT COUNT(*) AS n FROM time_slots")["n"],
        "scheduled":   db.fetchone("SELECT COUNT(*) AS n FROM schedules")["n"],
    }
    recent = db.fetchall("""
        SELECT s.id, c.code, c.name AS course_name,
               cl.name AS room, ts.slot_label, s.semester, s.year, s.algorithm_used
        FROM schedules s
        JOIN courses   c  ON s.course_id    = c.id
        JOIN classrooms cl ON s.classroom_id = cl.id
        JOIN time_slots ts ON s.time_slot_id = ts.id
        ORDER BY s.created_at DESC LIMIT 10
    """)
    return render_template("index.html", stats=stats, recent=recent)


# ─────────────────────────────────────────────────────────────
# Courses CRUD
# ─────────────────────────────────────────────────────────────

@app.route("/courses")
def courses():
    rows = db.fetchall("""
        SELECT c.*, i.name AS instructor_name, d.name AS dept_name
        FROM courses c
        LEFT JOIN instructors i ON c.instructor_id = i.id
        LEFT JOIN departments d ON c.department_id  = d.id
        ORDER BY c.code
    """)
    instructors = db.fetchall("SELECT * FROM instructors ORDER BY name")
    departments = db.fetchall("SELECT * FROM departments ORDER BY name")
    return render_template("courses.html",
                           courses=rows,
                           instructors=instructors,
                           departments=departments)


@app.route("/courses/add", methods=["POST"])
def add_course():
    f = request.form
    db.execute(
        """INSERT INTO courses (code, name, instructor_id, department_id,
                                credits, max_students, duration_hours)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (f["code"], f["name"], f.get("instructor_id") or None,
         f.get("department_id") or None,
         int(f.get("credits", 3)), int(f.get("max_students", 30)),
         float(f.get("duration_hours", 1.5)))
    )
    flash("Course added successfully.", "success")
    return redirect(url_for("courses"))


@app.route("/courses/delete/<int:cid>", methods=["POST"])
def delete_course(cid):
    db.execute("DELETE FROM courses WHERE id=%s", (cid,))
    flash("Course deleted.", "info")
    return redirect(url_for("courses"))


@app.route("/courses/edit/<int:cid>", methods=["POST"])
def edit_course(cid):
    f = request.form
    db.execute(
        """UPDATE courses SET code=%s, name=%s, instructor_id=%s,
                department_id=%s, credits=%s, max_students=%s, duration_hours=%s
           WHERE id=%s""",
        (f["code"], f["name"], f.get("instructor_id") or None,
         f.get("department_id") or None,
         int(f["credits"]), int(f["max_students"]),
         float(f["duration_hours"]), cid)
    )
    flash("Course updated.", "success")
    return redirect(url_for("courses"))




@app.route("/classrooms")
def classrooms():
    rooms = db.fetchall("SELECT * FROM classrooms ORDER BY building, name")
    return render_template("classrooms.html", classrooms=rooms)


@app.route("/classrooms/add", methods=["POST"])
def add_classroom():
    f = request.form
    db.execute(
        """INSERT INTO classrooms (name, building, capacity, has_projector, has_lab)
           VALUES (%s,%s,%s,%s,%s)""",
        (f["name"], f["building"], int(f["capacity"]),
         bool(f.get("has_projector")), bool(f.get("has_lab")))
    )
    flash("Classroom added.", "success")
    return redirect(url_for("classrooms"))


@app.route("/classrooms/delete/<int:rid>", methods=["POST"])
def delete_classroom(rid):
    db.execute("DELETE FROM classrooms WHERE id=%s", (rid,))
    flash("Classroom deleted.", "info")
    return redirect(url_for("classrooms"))



@app.route("/instructors")
def instructors():
    rows = db.fetchall("""
        SELECT i.*, d.name AS dept_name,
               COUNT(c.id) AS course_count
        FROM instructors i
        LEFT JOIN departments d ON i.department_id = d.id
        LEFT JOIN courses c ON c.instructor_id = i.id
        GROUP BY i.id
        ORDER BY i.name
    """)
    departments = db.fetchall("SELECT * FROM departments ORDER BY name")
    time_slots  = db.fetchall("SELECT * FROM time_slots ORDER BY day_of_week, start_time")
    return render_template("instructors.html",
                           instructors=rows,
                           departments=departments,
                           time_slots=time_slots)


@app.route("/instructors/add", methods=["POST"])
def add_instructor():
    f = request.form
    db.execute(
        "INSERT INTO instructors (name, email, department_id) VALUES (%s,%s,%s)",
        (f["name"], f["email"], f.get("department_id") or None)
    )
    flash("Instructor added.", "success")
    return redirect(url_for("instructors"))


@app.route("/instructors/delete/<int:iid>", methods=["POST"])
def delete_instructor(iid):
    db.execute("DELETE FROM instructors WHERE id=%s", (iid,))
    flash("Instructor deleted.", "info")
    return redirect(url_for("instructors"))


@app.route("/instructors/unavailability", methods=["POST"])
def set_unavailability():
    iid  = int(request.form["instructor_id"])
    tsids = request.form.getlist("time_slot_ids")
    db.execute("DELETE FROM instructor_unavailability WHERE instructor_id=%s", (iid,))
    for tsid in tsids:
        try:
            db.execute(
                "INSERT IGNORE INTO instructor_unavailability (instructor_id, time_slot_id) VALUES (%s,%s)",
                (iid, int(tsid))
            )
        except Exception:
            pass
    flash("Unavailability updated.", "success")
    return redirect(url_for("instructors"))



@app.route("/schedule")
def schedule():
    semester = request.args.get("semester", "Fall")
    year     = int(request.args.get("year", 2025))

    rows = db.fetchall("""
        SELECT s.id, c.code, c.name AS course_name, c.max_students,
               i.name AS instructor_name,
               cl.name AS room_name, cl.building, cl.capacity,
               ts.day_of_week, ts.start_time, ts.end_time, ts.slot_label,
               d.name AS dept_name, d.code AS dept_code,
               s.algorithm_used
        FROM schedules s
        JOIN courses    c  ON s.course_id    = c.id
        JOIN classrooms cl ON s.classroom_id = cl.id
        JOIN time_slots ts ON s.time_slot_id = ts.id
        LEFT JOIN instructors i ON c.instructor_id = i.id
        LEFT JOIN departments d ON c.department_id  = d.id
        WHERE s.semester=%s AND s.year=%s
        ORDER BY FIELD(ts.day_of_week,'Monday','Tuesday','Wednesday','Thursday','Friday'),
                 ts.start_time
    """, (semester, year))

    conflicts = db.fetchall("""
        SELECT cl.*, c.code, c.name AS course_name
        FROM conflict_log cl
        LEFT JOIN courses c ON cl.course_id = c.id
        WHERE cl.semester=%s AND cl.year=%s
        ORDER BY cl.created_at DESC
    """, (semester, year))

    semesters = [("Fall", 2025), ("Spring", 2026), ("Summer", 2026),
                 ("Fall", 2026), ("Spring", 2025)]

    return render_template("schedule.html",
                           schedule=rows,
                           conflicts=conflicts,
                           semester=semester,
                           year=year,
                           semesters=semesters)


@app.route("/schedule/generate", methods=["POST"])
def generate_schedule():
    semester  = request.form.get("semester", "Fall")
    year      = int(request.form.get("year", 2025))
    algorithm = request.form.get("algorithm", "hybrid")

    courses    = db.fetchall("SELECT * FROM courses ORDER BY max_students DESC")
    classrooms = db.fetchall("SELECT * FROM classrooms ORDER BY capacity")
    time_slots = db.fetchall(
        "SELECT * FROM time_slots ORDER BY FIELD(day_of_week,'Monday','Tuesday','Wednesday','Thursday','Friday'), start_time"
    )
    blocked = _get_blocked()

    _clear_schedule(semester, year)

    if algorithm == "greedy":
        result = greedy_schedule(courses, classrooms, time_slots, blocked)
    elif algorithm == "backtracking":
        result = backtracking_schedule(courses, classrooms, time_slots, blocked)
    else:
        result = hybrid_schedule(courses, classrooms, time_slots, blocked)

    # Persist assignments
    for a in result.assignments:
        try:
            db.execute(
                """INSERT INTO schedules (course_id, classroom_id, time_slot_id,
                                          semester, year, algorithm_used)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (a["course_id"], a["classroom_id"], a["time_slot_id"],
                 semester, year, a.get("algorithm", result.algorithm))
            )
        except Exception as e:
            print(f"Error persisting assignment: {e}")
            pass   # unique constraint – already scheduled

    # Persist conflicts
    for course in result.unscheduled:
        db.execute(
            """INSERT INTO conflict_log (course_id, conflict_type, description, semester, year)
               VALUES (%s,'Unscheduled',%s,%s,%s)""",
            (course["id"],
             f"Could not be scheduled by {result.algorithm}",
             semester, year)
        )

    flash(
        f"Schedule generated using {result.algorithm}. "
        f"{result.stats.get('total_scheduled', len(result.assignments))} courses scheduled, "
        f"{len(result.unscheduled)} unscheduled. "
        f"Time: {result.stats.get('elapsed_ms', '?')} ms",
        "success" if not result.unscheduled else "warning"
    )
    return redirect(url_for("schedule", semester=semester, year=year))


@app.route("/schedule/clear", methods=["POST"])
def clear_schedule():
    semester = request.form.get("semester", "Fall")
    year     = int(request.form.get("year", 2025))
    _clear_schedule(semester, year)
    flash(f"Schedule for {semester} {year} cleared.", "info")
    return redirect(url_for("schedule", semester=semester, year=year))


@app.route("/schedule/delete/<int:sid>", methods=["POST"])
def delete_schedule_entry(sid):
    row = db.fetchone("SELECT semester, year FROM schedules WHERE id=%s", (sid,))
    db.execute("DELETE FROM schedules WHERE id=%s", (sid,))
    flash("Entry removed.", "info")
    if row:
        return redirect(url_for("schedule", semester=row["semester"], year=row["year"]))
    return redirect(url_for("schedule"))


@app.route("/api/schedule")
def api_schedule():
    semester = request.args.get("semester", "Fall")
    year     = int(request.args.get("year", 2025))
    rows = db.fetchall("""
        SELECT s.id, c.code, c.name AS course_name,
               i.name AS instructor_name,
               cl.name AS room_name, cl.building,
               ts.day_of_week, ts.start_time, ts.end_time,
               s.algorithm_used
        FROM schedules s
        JOIN courses    c  ON s.course_id    = c.id
        JOIN classrooms cl ON s.classroom_id = cl.id
        JOIN time_slots ts ON s.time_slot_id = ts.id
        LEFT JOIN instructors i ON c.instructor_id = i.id
        WHERE s.semester=%s AND s.year=%s
    """, (semester, year))
    return jsonify(rows)


@app.route("/api/conflicts")
def api_conflicts():
    semester = request.args.get("semester", "Fall")
    year     = int(request.args.get("year", 2025))
    rows = db.fetchall("""
        SELECT cl.*, c.code
        FROM conflict_log cl
        LEFT JOIN courses c ON cl.course_id = c.id
        WHERE cl.semester=%s AND cl.year=%s
        ORDER BY cl.created_at DESC
    """, (semester, year))
    return jsonify(rows)


@app.route("/api/stats")
def api_stats():
    stats = {
        "courses":     db.fetchone("SELECT COUNT(*) AS n FROM courses")["n"],
        "classrooms":  db.fetchone("SELECT COUNT(*) AS n FROM classrooms")["n"],
        "instructors": db.fetchone("SELECT COUNT(*) AS n FROM instructors")["n"],
        "scheduled":   db.fetchone("SELECT COUNT(*) AS n FROM schedules")["n"],
    }
    return jsonify(stats)




@app.route("/timeslots")
def timeslots():
    slots = db.fetchall(
        "SELECT * FROM time_slots ORDER BY FIELD(day_of_week,'Monday','Tuesday','Wednesday','Thursday','Friday'), start_time"
    )
    return render_template("timeslots.html", time_slots=slots)


@app.route("/timeslots/add", methods=["POST"])
def add_timeslot():
    f = request.form
    label = f.get("slot_label") or f"{f['day_of_week'][:3]} {f['start_time']}–{f['end_time']}"
    db.execute(
        "INSERT IGNORE INTO time_slots (day_of_week, start_time, end_time, slot_label) VALUES (%s,%s,%s,%s)",
        (f["day_of_week"], f["start_time"], f["end_time"], label)
    )
    flash("Time slot added.", "success")
    return redirect(url_for("timeslots"))


@app.route("/timeslots/delete/<int:tsid>", methods=["POST"])
def delete_timeslot(tsid):
    db.execute("DELETE FROM time_slots WHERE id=%s", (tsid,))
    flash("Time slot deleted.", "info")
    return redirect(url_for("timeslots"))




if __name__ == "__main__":
    db.init_pool()
    app.run(debug=True, port=5000)
