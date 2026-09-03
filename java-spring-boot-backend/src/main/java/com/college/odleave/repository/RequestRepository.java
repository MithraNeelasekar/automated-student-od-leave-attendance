package com.college.odleave.repository;

import com.college.odleave.entity.Request;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface RequestRepository extends JpaRepository<Request, Long> {
    Optional<Request> findByRequestCode(String requestCode);
    List<Request> findByStudentIdOrderByCreatedAtDesc(Long studentId);
    List<Request> findByStatusOrderByCreatedAtAsc(Request.Status status);

    @Query("SELECT r FROM Request r WHERE r.student.id = :studentId " +
           "AND r.status IN ('PENDING_FACULTY', 'PENDING_HOD', 'APPROVED') " +
           "AND NOT (r.endDate < :startDate OR r.startDate > :endDate)")
    List<Request> findOverlappingActiveRequests(@Param("studentId") Long studentId,
                                                @Param("startDate") LocalDate startDate,
                                                @Param("endDate") LocalDate endDate);

    long countByRequestType(Request.RequestType requestType);
}
