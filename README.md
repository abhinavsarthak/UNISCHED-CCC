# 🎓 University Course Scheduling System

A full-stack web application that automates university course scheduling using
**Greedy** and **Backtracking** algorithms to assign courses to classrooms and
time slots while resolving all conflicts.

---

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Python 3.11 · Flask 3.0             |
| Database   | MySQL 8+ with connection pooling    |
| Algorithms | Greedy · Backtracking (CSP) · Hybrid|
| Frontend   | Jinja2 · Vanilla JS · Custom CSS    |

---

## Project Structure

```
university_scheduler/
├── app.py              # Flask routes & API endpoints
├── algorithms.py       # Greedy + Backtracking + Hybrid scheduling
├── database.py         # MySQL connection pool & query helpers
├── setup.sql           # Schema + seed data
├── requirements.txt
├── .env.example        # Environment variables template
├── templates/
│   ├── base.html       # Sidebar layout + nav
│   ├── index.html      # Dashboard
│   ├── courses.html    # Course CRUD
│   ├── classrooms.html # Classroom CRUD
│   ├── instructors.html# Instructor management + availability
│   ├── timeslots.html  # Time slot management
│   └── schedule.html   # Schedule generation + timetable view
└── static/
    ├── css/style.css   # Dark academic theme
    └── js/main.js      # Modal, UI interactions
```

---

## Setup & Installation

### 1. Clone / download

```bash
cd university_scheduler
```

### 2. Python environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. MySQL database

```bash
mysql -u root -p < setup.sql
```

This creates the `university_scheduler` database with all tables and sample data
(6 departments, 10 instructors, 15 courses, 10 classrooms, 25 time slots).

### 4. Environment variables

```bash
cp .env.example .env
# Edit .env with your MySQL credentials
```

### 5. Run

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## Database Schema

```
departments         instructors          courses
──────────         ────────────         ───────
id                 id                   id
name               name                 code
code               email                name
                   department_id ──→    instructor_id ──→ instructors
                                        department_id ──→ departments
                                        credits
                                        max_students
                                        duration_hours

classrooms         time_slots           schedules
──────────         ──────────           ─────────
id                 id                   id
name               day_of_week          course_id ──→ courses
building           start_time           classroom_id ──→ classrooms
capacity           end_time             time_slot_id ──→ time_slots
has_projector      slot_label           semester
has_lab                                 year
                                        algorithm_used

instructor_unavailability    conflict_log
─────────────────────────    ────────────
instructor_id                id
time_slot_id                 course_id
reason                       conflict_type
                             description
```

---

## Algorithms

### Greedy Algorithm

**Complexity:** O(n × m × t) where n = courses, m = rooms, t = time slots.

```
Sort courses by max_students DESC  (most constrained first)
For each course:
  For each time_slot in order:
    For each classroom (smallest capacity first):
      If passes all constraints → assign and break
  If no slot found → mark as unscheduled
```

**Constraints checked:**
- Room capacity ≥ course enrolment
- Room not already booked at this time
- Instructor not already teaching at this time
- Instructor not marked unavailable at this time

**Pros:** Very fast (typically < 5 ms for 15 courses).  
**Cons:** Not guaranteed to find a solution even if one exists.

---

### Backtracking Algorithm (CSP Solver)

Implements a **Constraint Satisfaction Problem** solver with three key
optimisations:

#### MRV — Minimum Remaining Values
Select the course with the fewest valid (room, slot) pairs first. This
catches dead-ends early and reduces search space dramatically.

#### LCV — Least Constraining Value
When assigning a value, prefer values that remove the fewest options from
other unassigned courses. This increases the chance of completing the
assignment without needing to backtrack.

#### Forward Checking
After each assignment, prune the domains of remaining courses to remove
values that are now invalid. If any domain becomes empty, backtrack
immediately without going deeper.

```
procedure BACKTRACK(assignment, domains):
  if assignment is complete → return SUCCESS

  course ← SELECT-UNASSIGNED-MRV(domains)
  for (room, slot) in ORDER-DOMAIN-LCV(course, domains):
    if CONSISTENT(assignment, course, room, slot):
      assign course → (room, slot)
      if FORWARD-CHECK(course, room, slot, domains):
        result ← BACKTRACK(assignment, domains)
        if result ≠ FAILURE → return result
      unassign course
  return FAILURE
```

**Hard cap:** 500,000 backtracks to keep the demo responsive.

---

### Hybrid Algorithm (Recommended)

1. Run **Greedy** on all courses.
2. Collect any courses Greedy couldn't place.
3. Run **Backtracking** only on those remaining courses, with the greedy
   assignments already locked in.

This gives the speed of Greedy for straightforward cases and the
completeness of Backtracking for difficult constraint clusters.

---

## API Endpoints

| Method | URL                        | Description                    |
|--------|----------------------------|--------------------------------|
| GET    | `/api/schedule`            | Schedule as JSON (semester/year params) |
| GET    | `/api/conflicts`           | Conflict log as JSON            |
| GET    | `/api/stats`               | Summary statistics              |
| POST   | `/schedule/generate`       | Run scheduling algorithm        |
| POST   | `/schedule/clear`          | Clear a semester schedule       |

---

## Features

- **Dashboard** with live statistics and algorithm descriptions
- **Course CRUD** — add/edit/delete courses with instructor and department links
- **Classroom CRUD** — manage room capacity, projector, lab flags
- **Instructor Management** — set per-instructor unavailability blocks
- **Time Slot Management** — configure the weekly slot grid
- **Schedule Generation** — choose Greedy / Backtracking / Hybrid
- **Timetable View** — visual weekly grid with colour-coded algorithm badges
- **Conflict Log** — see exactly which courses couldn't be placed and why
- **Semester Switcher** — manage multiple semester schedules independently

---

## Screenshots

The interface uses a **dark academic theme** with:
- Deep navy background (`#0d1117`)  
- Amber accent colour (`#f5a623`)  
- DM Serif Display + Syne + IBM Plex Mono typography  
- Animated stat counters, smooth modals, and a CSS grid timetable

---

## License

MIT
