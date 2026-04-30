"""
algorithms.py
=============
Greedy + Backtracking course-scheduling algorithms.

Data structures passed in / returned
-------------------------------------
courses   : list of dicts  {id, code, name, instructor_id, max_students, ...}
classrooms: list of dicts  {id, name, capacity, ...}
time_slots: list of dicts  {id, slot_label, day_of_week, start_time, end_time}
blocked   : dict           {instructor_id: set(time_slot_ids)}   ← unavailability

Returns
-------
ScheduleResult dataclass with:
  assignments : list of {course_id, classroom_id, time_slot_id}
  unscheduled : list of course dicts that could not be placed
  conflicts   : list of conflict description strings
  algorithm   : "Greedy" | "Backtracking"
  stats       : dict of timing / step counts
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field


# ──────────────────────────────────────────────
# Domain types
# ──────────────────────────────────────────────

@dataclass
class ScheduleResult:
    assignments: list[dict] = field(default_factory=list)
    unscheduled: list[dict] = field(default_factory=list)
    conflicts:   list[str]  = field(default_factory=list)
    algorithm:   str        = "Greedy"
    stats:       dict       = field(default_factory=dict)


# ──────────────────────────────────────────────
# Constraint checker (shared by both algorithms)
# ──────────────────────────────────────────────

class ConstraintChecker:
    """Tracks existing assignments and validates new ones."""

    def __init__(self, blocked: dict[int, set]):
        # blocked[instructor_id] = {time_slot_id, ...}
        self.blocked: dict[int, set] = blocked
        # room_time[(classroom_id, time_slot_id)] = course_id
        self.room_time: dict[tuple, int] = {}
        # instructor_time[(instructor_id, time_slot_id)] = course_id
        self.inst_time: dict[tuple, int] = {}

    # ---------- validation ----------
    def can_assign(self, course: dict, classroom: dict, ts_id: int) -> tuple[bool, str]:
        c_id  = course["id"]
        r_id  = classroom["id"]
        i_id  = course.get("instructor_id")

        # 1. Capacity
        if classroom["capacity"] < course["max_students"]:
            return False, (
                f"Room {classroom['name']} (cap {classroom['capacity']}) "
                f"< course enrolment {course['max_students']}"
            )

        # 2. Room clash
        if (r_id, ts_id) in self.room_time:
            return False, (
                f"Room {classroom['name']} already booked at slot {ts_id} "
                f"(by course id {self.room_time[(r_id, ts_id)]})"
            )

        # 3. Instructor clash
        if i_id and (i_id, ts_id) in self.inst_time:
            return False, (
                f"Instructor {i_id} already teaching at slot {ts_id}"
            )

        # 4. Instructor unavailability
        if i_id and ts_id in self.blocked.get(i_id, set()):
            return False, f"Instructor {i_id} unavailable at slot {ts_id}"

        return True, ""

    # ---------- commit / rollback ----------
    def assign(self, course: dict, classroom: dict, ts_id: int) -> None:
        self.room_time[(classroom["id"], ts_id)] = course["id"]
        if course.get("instructor_id"):
            self.inst_time[(course["instructor_id"], ts_id)] = course["id"]

    def unassign(self, course: dict, classroom: dict, ts_id: int) -> None:
        self.room_time.pop((classroom["id"], ts_id), None)
        if course.get("instructor_id"):
            self.inst_time.pop((course["instructor_id"], ts_id), None)

    def clone(self) -> "ConstraintChecker":
        c = ConstraintChecker(self.blocked)
        c.room_time = dict(self.room_time)
        c.inst_time = dict(self.inst_time)
        return c


# ──────────────────────────────────────────────
# Greedy Algorithm
# ──────────────────────────────────────────────

def greedy_schedule(
    courses:    list[dict],
    classrooms: list[dict],
    time_slots: list[dict],
    blocked:    dict[int, set],
) -> ScheduleResult:
    """
    Greedy heuristic
    ----------------
    1. Sort courses by max_students DESC (most constrained first — they need
       bigger rooms and get first pick).
    2. For each course iterate time-slots then classrooms; take the first
       combination that passes all constraints.
    """
    t0     = time.perf_counter()
    result = ScheduleResult(algorithm="Greedy")
    checker = ConstraintChecker(blocked)

    ts_ids = [ts["id"] for ts in time_slots]
    sorted_courses = sorted(courses, key=lambda c: c["max_students"], reverse=True)

    for course in sorted_courses:
        placed = False
        for ts in time_slots:
            for room in sorted(classrooms, key=lambda r: r["capacity"]):
                ok, reason = checker.can_assign(course, room, ts["id"])
                if ok:
                    checker.assign(course, room, ts["id"])
                    result.assignments.append({
                        "course_id":    course["id"],
                        "classroom_id": room["id"],
                        "time_slot_id": ts["id"],
                        "algorithm":    "Greedy",
                    })
                    placed = True
                    break
            if placed:
                break

        if not placed:
            result.unscheduled.append(course)
            result.conflicts.append(
                f"[GREEDY] Could not schedule '{course['code']} – {course['name']}'"
            )

    elapsed = time.perf_counter() - t0
    result.stats = {
        "elapsed_ms":  round(elapsed * 1000, 2),
        "total":       len(courses),
        "scheduled":   len(result.assignments),
        "unscheduled": len(result.unscheduled),
    }
    return result


# ──────────────────────────────────────────────
# Backtracking Algorithm
# ──────────────────────────────────────────────

# Hard cap to keep the demo responsive
MAX_BACKTRACKS = 500_000


def backtracking_schedule(
    courses:    list[dict],
    classrooms: list[dict],
    time_slots: list[dict],
    blocked:    dict[int, set],
    initial_checker: ConstraintChecker | None = None,
) -> ScheduleResult:
    """
    Backtracking with constraint propagation
    ----------------------------------------
    Variables   : courses (ordered by degree heuristic – most constrained first)
    Domains     : (classroom, time_slot) pairs that satisfy hard constraints for
                  each course even before backtracking starts (forward checking).
    Constraints : capacity, room-clash, instructor-clash, unavailability.

    Optimisations
    ~~~~~~~~~~~~~
    * Minimum Remaining Values (MRV): pick course whose domain is smallest.
    * Forward checking: prune domains of un-assigned courses after each commit.
    * Least Constraining Value (LCV): choose the value that prunes the fewest
      other domains first.
    """
    t0 = time.perf_counter()
    result = ScheduleResult(algorithm="Backtracking")
    backtracks  = 0
    assignments: dict[int, tuple[dict, dict, int]] = {}   # course_id → (course, room, ts_id)
    checker    = initial_checker.clone() if initial_checker else ConstraintChecker(blocked)

    # Pre-compute initial domains
    def initial_domain(course: dict) -> list[tuple[dict, int]]:
        dom = []
        for ts in time_slots:
            ts_id = ts["id"]
            if course.get("instructor_id") and ts_id in blocked.get(course["instructor_id"], set()):
                continue
            for room in classrooms:
                ok, _ = checker.can_assign(course, room, ts_id)
                if ok:
                    dom.append((room, ts_id))
        return dom

    domains: dict[int, list[tuple[dict, int]]] = {
        c["id"]: initial_domain(c) for c in courses
    }
    course_map: dict[int, dict] = {c["id"]: c for c in courses}
    unassigned = [c["id"] for c in courses]

    # ── MRV variable selector ──
    def select_unassigned() -> int | None:
        if not unassigned:
            return None
        return min(unassigned, key=lambda cid: len(domains[cid]))

    # ── LCV value ordering ──
    def order_values(cid: int) -> list[tuple[dict, int]]:
        """Return domain values sorted by how few domains they constrain."""
        def count_conflicts(room: dict, ts_id: int) -> int:
            n = 0
            for other_cid in unassigned:
                if other_cid == cid:
                    continue
                for (r2, ts2) in domains[other_cid]:
                    if (r2["id"] == room["id"] and ts2 == ts_id):
                        n += 1
                    if (course_map[cid].get("instructor_id")
                            and course_map[other_cid].get("instructor_id") == course_map[cid]["instructor_id"]
                            and ts2 == ts_id):
                        n += 1
            return n
        return sorted(domains[cid], key=lambda v: count_conflicts(v[0], v[1]))

    # ── Forward checking ──
    def forward_check(cid: int, room: dict, ts_id: int) -> bool:
        """Prune domains; return False if any domain becomes empty."""
        for other_cid in unassigned:
            if other_cid == cid:
                continue
            other_course = course_map[other_cid]
            pruned = []
            for (r2, ts2) in domains[other_cid]:
                # room clash
                if r2["id"] == room["id"] and ts2 == ts_id:
                    continue
                # instructor clash
                if (course_map[cid].get("instructor_id")
                        and other_course.get("instructor_id") == course_map[cid]["instructor_id"]
                        and ts2 == ts_id):
                    continue
                pruned.append((r2, ts2))
            if not pruned:
                return False          # domain wipe-out
            domains[other_cid] = pruned
        return True

    # ── Recursive backtracking ──
    def backtrack() -> bool:
        nonlocal backtracks
        if not unassigned:
            return True                # all assigned ✓
        if backtracks >= MAX_BACKTRACKS:
            return False               # bail out

        cid    = select_unassigned()
        course = course_map[cid]
        unassigned.remove(cid)

        saved_domains = {c: list(domains[c]) for c in unassigned}   # snapshot

        for (room, ts_id) in order_values(cid):
            ok, _ = checker.can_assign(course, room, ts_id)
            if not ok:
                continue

            checker.assign(course, room, ts_id)
            assignments[cid] = (course, room, ts_id)

            # Forward-check before recursing
            if forward_check(cid, room, ts_id) and backtrack():
                return True

            # Undo
            checker.unassign(course, room, ts_id)
            del assignments[cid]
            for c in unassigned:
                domains[c] = list(saved_domains[c])

            backtracks += 1

        # No value worked → backtrack
        unassigned.append(cid)
        return False

    success = backtrack()

    for cid, (course, room, ts_id) in assignments.items():
        result.assignments.append({
            "course_id":    cid,
            "classroom_id": room["id"],
            "time_slot_id": ts_id,
            "algorithm":    "Backtracking",
        })

    if not success:
        for cid in unassigned:
            result.unscheduled.append(course_map[cid])
            result.conflicts.append(
                f"[BACKTRACKING] No valid slot found for '{course_map[cid]['code']}'"
            )

    elapsed = time.perf_counter() - t0
    result.stats = {
        "elapsed_ms":  round(elapsed * 1000, 2),
        "backtracks":  backtracks,
        "total":       len(courses),
        "scheduled":   len(result.assignments),
        "unscheduled": len(result.unscheduled),
        "success":     success,
    }
    return result


# ──────────────────────────────────────────────
# Hybrid: Greedy first, then Backtracking for remainders
# ──────────────────────────────────────────────

def hybrid_schedule(
    courses:    list[dict],
    classrooms: list[dict],
    time_slots: list[dict],
    blocked:    dict[int, set],
) -> ScheduleResult:
    """
    Phase 1 – Greedy (fast path for the easy cases).
    Phase 2 – Backtracking only for courses Greedy could not place.
    """
    greedy = greedy_schedule(courses, classrooms, time_slots, blocked)

    if not greedy.unscheduled:
        greedy.algorithm = "Greedy + Backtracking"
        greedy.stats["total_scheduled"] = greedy.stats["scheduled"]
        greedy.stats["greedy_scheduled"] = greedy.stats["scheduled"]
        greedy.stats["backtracking_scheduled"] = 0
        greedy.stats["bt_backtracks"] = 0
        return greedy           # Greedy got them all

    # Rebuild checker state from greedy assignments
    checker2 = ConstraintChecker(blocked)
    course_map = {c["id"]: c for c in courses}
    room_map   = {r["id"]: r for r in classrooms}
    for a in greedy.assignments:
        checker2.assign(course_map[a["course_id"]], room_map[a["classroom_id"]], a["time_slot_id"])

    bt = backtracking_schedule(
        greedy.unscheduled, classrooms, time_slots, blocked, initial_checker=checker2
    )

    # Merge
    combined              = ScheduleResult(algorithm="Greedy + Backtracking")
    combined.assignments  = greedy.assignments + bt.assignments
    combined.unscheduled  = bt.unscheduled
    combined.conflicts    = greedy.conflicts + bt.conflicts
    combined.stats        = {
        "greedy_scheduled":      greedy.stats["scheduled"],
        "backtracking_scheduled":bt.stats["scheduled"],
        "total_scheduled":       len(combined.assignments),
        "unscheduled":           len(combined.unscheduled),
        "bt_backtracks":         bt.stats.get("backtracks", 0),
        "elapsed_ms":            round(
            greedy.stats["elapsed_ms"] + bt.stats["elapsed_ms"], 2
        ),
    }
    return combined
