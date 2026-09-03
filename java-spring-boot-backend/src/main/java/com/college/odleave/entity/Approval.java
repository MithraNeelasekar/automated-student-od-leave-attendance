package com.college.odleave.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "approvals")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Approval {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "request_id", nullable = false)
    private Request request;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "approver_id", nullable = false)
    private User approver;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private User.Role approverRole;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private Action action;

    @Column(columnDefinition = "TEXT")
    private String remarks;

    @Column(name = "action_date", updatable = false)
    @Builder.Default
    private LocalDateTime actionDate = LocalDateTime.now();

    public enum Action {
        SUBMITTED,
        FACULTY_APPROVED,
        FACULTY_REJECTED,
        HOD_APPROVED,
        HOD_REJECTED
    }
}
