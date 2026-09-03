-- =========================================================================
-- AUTOMATED STUDENT OD AND LEAVE APPROVAL WITH ATTENDANCE INTEGRATION
-- MySQL Relational Database Schema
-- =========================================================================

CREATE DATABASE IF NOT EXISTS college_od_leave_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE college_od_leave_db;

-- Drop existing tables in reverse dependency order
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS approvals;
DROP TABLE IF EXISTS requests;
DROP TABLE IF EXISTS subjects;
DROP TABLE IF EXISTS faculty;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. USERS TABLE
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('STUDENT', 'FACULTY', 'HOD_ADMIN') NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_role (role),
    INDEX idx_user_email (email)
) ENGINE=InnoDB;

-- 2. FACULTY TABLE
CREATE TABLE faculty (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    faculty_id VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    designation VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_fac_dept (department)
) ENGINE=InnoDB;

-- 3. STUDENTS TABLE
CREATE TABLE students (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    register_number VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    year INT NOT NULL,
    section VARCHAR(10) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    mentor_faculty_id BIGINT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (mentor_faculty_id) REFERENCES faculty(id) ON DELETE SET NULL,
    INDEX idx_student_dept_yr (department, year, section),
    INDEX idx_student_regno (register_number)
) ENGINE=InnoDB;

-- 4. SUBJECTS TABLE
CREATE TABLE subjects (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(20) NOT NULL UNIQUE,
    subject_name VARCHAR(150) NOT NULL,
    department VARCHAR(50) NOT NULL,
    year INT NOT NULL,
    semester INT NOT NULL,
    faculty_id BIGINT NULL,
    total_classes INT NOT NULL DEFAULT 40,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE SET NULL,
    INDEX idx_subject_curriculum (department, year, semester)
) ENGINE=InnoDB;

-- 5. REQUESTS TABLE (OD & Leave)
CREATE TABLE requests (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    request_code VARCHAR(30) NOT NULL UNIQUE,
    student_id BIGINT NOT NULL,
    request_type ENUM('OD', 'LEAVE') NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    event_name VARCHAR(200) NULL,
    event_type VARCHAR(100) NULL,
    venue VARCHAR(200) NULL,
    leave_type VARCHAR(100) NULL,
    reason TEXT NOT NULL,
    document_name VARCHAR(255) NULL,
    document_path VARCHAR(500) NULL,
    status ENUM('PENDING_FACULTY', 'PENDING_HOD', 'APPROVED', 'REJECTED_FACULTY', 'REJECTED_HOD') NOT NULL DEFAULT 'PENDING_FACULTY',
    attendance_updated TINYINT(1) NOT NULL DEFAULT 0,
    student_remarks TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    INDEX idx_req_student (student_id),
    INDEX idx_req_status (status),
    INDEX idx_req_dates (start_date, end_date)
) ENGINE=InnoDB;

-- 6. APPROVALS TABLE (Multi-tier Audit Log)
CREATE TABLE approvals (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    request_id BIGINT NOT NULL,
    approver_id BIGINT NOT NULL,
    approver_role ENUM('STUDENT', 'FACULTY', 'HOD_ADMIN') NOT NULL,
    action ENUM('SUBMITTED', 'FACULTY_APPROVED', 'FACULTY_REJECTED', 'HOD_APPROVED', 'HOD_REJECTED') NOT NULL,
    remarks TEXT NULL,
    action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE,
    FOREIGN KEY (approver_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_approval_request (request_id)
) ENGINE=InnoDB;

-- 7. ATTENDANCE TABLE (With Idempotency Unique Constraint & OD Linkage)
CREATE TABLE attendance (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    student_id BIGINT NOT NULL,
    subject_id BIGINT NOT NULL,
    attendance_date DATE NOT NULL,
    status ENUM('PRESENT', 'ABSENT', 'ON_DUTY') NOT NULL,
    source ENUM('REGULAR', 'OD_INTEGRATION') NOT NULL DEFAULT 'REGULAR',
    request_id BIGINT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE SET NULL,
    UNIQUE KEY uq_student_subject_date (student_id, subject_id, attendance_date),
    INDEX idx_att_date_status (attendance_date, status)
) ENGINE=InnoDB;

-- 8. NOTIFICATIONS TABLE
CREATE TABLE notifications (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    link VARCHAR(100) NULL,
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_notif_user_read (user_id, is_read)
) ENGINE=InnoDB;
