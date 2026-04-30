-- ============================================================
--   University Course Scheduling System - Database Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS university_scheduler CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE university_scheduler;

-- Departments
CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Instructors
CREATE TABLE IF NOT EXISTS instructors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    department_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
);

-- Courses
CREATE TABLE IF NOT EXISTS courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    instructor_id INT,
    department_id INT,
    credits INT DEFAULT 3,
    max_students INT DEFAULT 30,
    duration_hours DECIMAL(3,1) DEFAULT 1.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instructor_id) REFERENCES instructors(id) ON DELETE SET NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
);

-- Classrooms
CREATE TABLE IF NOT EXISTS classrooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    building VARCHAR(100) NOT NULL,
    capacity INT NOT NULL,
    has_projector BOOLEAN DEFAULT FALSE,
    has_lab BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Time Slots (Mon-Fri, standard university schedule)
CREATE TABLE IF NOT EXISTS time_slots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    day_of_week ENUM('Monday','Tuesday','Wednesday','Thursday','Friday') NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_label VARCHAR(80),
    UNIQUE KEY unique_slot (day_of_week, start_time, end_time)
);

-- Instructor Unavailability (blocked time slots)
CREATE TABLE IF NOT EXISTS instructor_unavailability (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instructor_id INT NOT NULL,
    time_slot_id INT NOT NULL,
    reason VARCHAR(200),
    FOREIGN KEY (instructor_id) REFERENCES instructors(id) ON DELETE CASCADE,
    FOREIGN KEY (time_slot_id) REFERENCES time_slots(id) ON DELETE CASCADE,
    UNIQUE KEY unique_unavail (instructor_id, time_slot_id)
);

-- Schedule (final assignments)
CREATE TABLE IF NOT EXISTS schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    classroom_id INT NOT NULL,
    time_slot_id INT NOT NULL,
    semester ENUM('Fall','Spring','Summer') NOT NULL,
    year INT NOT NULL,
    algorithm_used ENUM('Greedy','Backtracking','Manual') DEFAULT 'Greedy',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_schedule (course_id, semester, year),
    UNIQUE KEY no_room_clash (classroom_id, time_slot_id, semester, year),
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE,
    FOREIGN KEY (time_slot_id) REFERENCES time_slots(id) ON DELETE CASCADE
);

-- Conflict log
CREATE TABLE IF NOT EXISTS conflict_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT,
    conflict_type ENUM('Room_Clash','Instructor_Clash','Capacity_Exceeded','Unscheduled'),
    description TEXT,
    semester ENUM('Fall','Spring','Summer'),
    year INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
);

-- ============================================================
--  Seed Data
-- ============================================================

INSERT INTO departments (name, code) VALUES
('Computer Science', 'CS'),
('Mathematics', 'MATH'),
('Physics', 'PHY'),
('Business Administration', 'BUS'),
('Electrical Engineering', 'EE'),
('Data Science', 'DS');

INSERT INTO instructors (name, email, department_id) VALUES
('Dr. Sarah Mitchell',    'smitchell@univ.edu',  1),
('Prof. James Thornton',  'jthornton@univ.edu',  1),
('Dr. Amelia Patel',      'apatel@univ.edu',     2),
('Prof. Robert Chen',     'rchen@univ.edu',      3),
('Dr. Lisa Okonkwo',      'lokonkwo@univ.edu',   4),
('Prof. Marcus Williams', 'mwilliams@univ.edu',  5),
('Dr. Priya Sharma',      'psharma@univ.edu',    6),
('Prof. David Kowalski',  'dkowalski@univ.edu',  2),
('Dr. Elena Vasquez',     'evasquez@univ.edu',   1),
('Prof. Nathan Brooks',   'nbrooks@univ.edu',    4);

INSERT INTO courses (code, name, instructor_id, department_id, credits, max_students, duration_hours) VALUES
('CS101',  'Introduction to Programming',       1, 1, 3, 40, 1.5),
('CS201',  'Data Structures & Algorithms',      2, 1, 3, 35, 1.5),
('CS301',  'Database Management Systems',       9, 1, 3, 30, 1.5),
('CS401',  'Machine Learning Fundamentals',     7, 1, 3, 25, 1.5),
('MATH101','Calculus I',                        3, 2, 4, 45, 1.5),
('MATH201','Linear Algebra',                    8, 2, 3, 35, 1.5),
('MATH301','Differential Equations',            3, 2, 3, 30, 1.5),
('PHY101', 'Physics I: Mechanics',              4, 3, 4, 50, 1.5),
('BUS101', 'Principles of Management',          5, 4, 3, 55, 1.5),
('BUS201', 'Marketing Fundamentals',           10, 4, 3, 40, 1.5),
('EE101',  'Circuit Analysis',                  6, 5, 4, 30, 1.5),
('EE201',  'Digital Electronics',               6, 5, 3, 25, 1.5),
('DS101',  'Introduction to Data Science',      7, 6, 3, 35, 1.5),
('DS201',  'Statistical Learning',              7, 6, 3, 28, 1.5),
('CS501',  'Software Engineering',              1, 1, 3, 30, 1.5);

INSERT INTO classrooms (name, building, capacity, has_projector, has_lab) VALUES
('Room 101',   'Main Hall',         40,  TRUE,  FALSE),
('Room 102',   'Main Hall',         35,  TRUE,  FALSE),
('Room 201',   'Science Block',     30,  TRUE,  FALSE),
('Room 202',   'Science Block',     25,  FALSE, FALSE),
('Lab A',      'Tech Building',     30,  TRUE,  TRUE),
('Lab B',      'Tech Building',     25,  TRUE,  TRUE),
('Auditorium', 'Central Campus',    60,  TRUE,  FALSE),
('Room 301',   'Business School',   45,  TRUE,  FALSE),
('Room 302',   'Business School',   40,  FALSE, FALSE),
('Room 401',   'Engineering Block', 30,  TRUE,  FALSE);

INSERT INTO time_slots (day_of_week, start_time, end_time, slot_label) VALUES
('Monday',    '08:00:00', '09:30:00',  'Mon 08:00–09:30'),
('Monday',    '09:45:00', '11:15:00',  'Mon 09:45–11:15'),
('Monday',    '11:30:00', '13:00:00',  'Mon 11:30–13:00'),
('Monday',    '14:00:00', '15:30:00',  'Mon 14:00–15:30'),
('Monday',    '15:45:00', '17:15:00',  'Mon 15:45–17:15'),
('Tuesday',   '08:00:00', '09:30:00',  'Tue 08:00–09:30'),
('Tuesday',   '09:45:00', '11:15:00',  'Tue 09:45–11:15'),
('Tuesday',   '11:30:00', '13:00:00',  'Tue 11:30–13:00'),
('Tuesday',   '14:00:00', '15:30:00',  'Tue 14:00–15:30'),
('Tuesday',   '15:45:00', '17:15:00',  'Tue 15:45–17:15'),
('Wednesday', '08:00:00', '09:30:00',  'Wed 08:00–09:30'),
('Wednesday', '09:45:00', '11:15:00',  'Wed 09:45–11:15'),
('Wednesday', '11:30:00', '13:00:00',  'Wed 11:30–13:00'),
('Wednesday', '14:00:00', '15:30:00',  'Wed 14:00–15:30'),
('Wednesday', '15:45:00', '17:15:00',  'Wed 15:45–17:15'),
('Thursday',  '08:00:00', '09:30:00',  'Thu 08:00–09:30'),
('Thursday',  '09:45:00', '11:15:00',  'Thu 09:45–11:15'),
('Thursday',  '11:30:00', '13:00:00',  'Thu 11:30–13:00'),
('Thursday',  '14:00:00', '15:30:00',  'Thu 14:00–15:30'),
('Thursday',  '15:45:00', '17:15:00',  'Thu 15:45–17:15'),
('Friday',    '08:00:00', '09:30:00',  'Fri 08:00–09:30'),
('Friday',    '09:45:00', '11:15:00',  'Fri 09:45–11:15'),
('Friday',    '11:30:00', '13:00:00',  'Fri 11:30–13:00'),
('Friday',    '14:00:00', '15:30:00',  'Fri 14:00–15:30'),
('Friday',    '15:45:00', '17:15:00',  'Fri 15:45–17:15');
