package com.college.odleave.repository;

import com.college.odleave.entity.Attendance;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface AttendanceRepository extends JpaRepository<Attendance, Long> {
    List<Attendance> findByStudentIdOrderByAttendanceDateDesc(Long studentId);
    List<Attendance> findByStudentIdAndSubjectId(Long studentId, Long subjectId);
    Optional<Attendance> findByStudentIdAndSubjectIdAndAttendanceDate(Long studentId, Long subjectId, LocalDate date);
    long countByStudentIdAndSubjectIdAndStatus(Long studentId, Long subjectId, Attendance.AttendanceStatus status);
    long countByStudentIdAndSubjectId(Long studentId, Long subjectId);
}
