package com.college.odleave.repository;

import com.college.odleave.entity.Subject;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface SubjectRepository extends JpaRepository<Subject, Long> {
    Optional<Subject> findBySubjectCode(String subjectCode);
    List<Subject> findByDepartmentAndYear(String department, Integer year);
    List<Subject> findByFacultyId(Long facultyId);
}
