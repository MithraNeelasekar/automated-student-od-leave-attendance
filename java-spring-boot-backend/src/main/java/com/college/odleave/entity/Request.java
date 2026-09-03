package com.college.odleave.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "requests")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Request {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 30)
    private String requestCode;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "student_id", nullable = false)
    private Student student;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private RequestType requestType;

    @Column(nullable = false)
    private LocalDate startDate;

    @Column(nullable = false)
    private LocalDate endDate;

    @Column(length = 200)
    private String eventName;

    @Column(length = 100)
    private String eventType;

    @Column(length = 200)
    private String venue;

    @Column(length = 100)
    private String leaveType;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String reason;

    @Column(length = 255)
    private String documentName;

    @Column(length = 500)
    private String documentPath;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    @Builder.Default
    private Status status = Status.PENDING_FACULTY;

    @Column(nullable = false)
    @Builder.Default
    private Boolean attendanceUpdated = false;

    @Column(columnDefinition = "TEXT")
    private String studentRemarks;

    @Column(name = "created_at", updatable = false)
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    @Builder.Default
    private LocalDateTime updatedAt = LocalDateTime.now();

    public enum RequestType {
        OD,
        LEAVE
    }

    public enum Status {
        PENDING_FACULTY,
        PENDING_HOD,
        APPROVED,
        REJECTED_FACULTY,
        REJECTED_HOD
    }
}
