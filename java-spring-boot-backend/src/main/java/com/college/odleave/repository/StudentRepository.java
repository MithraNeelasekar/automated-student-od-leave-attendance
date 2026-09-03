package com.college.odleave.repository;

import com.college.odleave.entity.Student;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface StudentRepository extends JpaRepository<Student, Long> {
    Optional<Student> findByUserId(Long userId);
    Optional<Student> findByRegisterNumber(String registerNumber);
    List<Student> findByDepartmentAndYear(String department, Integer year);
    List<Student> findByMentorFacultyId(Long facultyId);
}
