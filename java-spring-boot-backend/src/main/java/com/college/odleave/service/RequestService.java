package com.college.odleave.service;

import com.college.odleave.dto.LeaveRequestDto;
import com.college.odleave.dto.OdRequestDto;
import com.college.odleave.entity.Approval;
import com.college.odleave.entity.Faculty;
import com.college.odleave.entity.Request;
import com.college.odleave.entity.Student;
import com.college.odleave.entity.User;
import com.college.odleave.repository.ApprovalRepository;
import com.college.odleave.repository.RequestRepository;
import com.college.odleave.repository.StudentRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class RequestService {

    private final RequestRepository requestRepository;
    private final ApprovalRepository approvalRepository;
    private final StudentRepository studentRepository;
    private final AttendanceIntegrationService attendanceIntegrationService;
    private final NotificationService notificationService;

    @Transactional
    public Request submitOdRequest(Long studentId, OdRequestDto dto, String docName, String docPath) {
        Student student = studentRepository.findById(studentId)
                .orElseThrow(() -> new IllegalArgumentException("Student not found"));

        LocalDate endDate = dto.getEndDate() != null ? dto.getEndDate() : dto.getStartDate();
        if (endDate.isBefore(dto.getStartDate())) {
            throw new IllegalArgumentException("End date cannot be earlier than start date");
        }

        // Check overlapping active requests
        List<Request> overlaps = requestRepository.findOverlappingActiveRequests(studentId, dto.getStartDate(), endDate);
        if (!overlaps.isEmpty()) {
            throw new IllegalArgumentException("An active request already exists for this date range.");
        }

        long count = requestRepository.countByRequestType(Request.RequestType.OD) + 1;
        String requestCode = String.format("OD-%d-%03d", LocalDate.now().getYear(), count);

        Request request = Request.builder()
                .requestCode(requestCode)
                .student(student)
                .requestType(Request.RequestType.OD)
                .startDate(dto.getStartDate())
                .endDate(endDate)
                .eventName(dto.getEventName())
                .eventType(dto.getEventType())
                .venue(dto.getVenue())
                .reason(dto.getReason())
                .documentName(docName)
                .documentPath(docPath)
                .studentRemarks(dto.getRemarks())
                .status(Request.Status.PENDING_FACULTY)
                .attendanceUpdated(false)
                .build();

        Request saved = requestRepository.save(request);

        // Initial submission approval audit
        Approval approval = Approval.builder()
                .request(saved)
                .approver(student.getUser())
                .approverRole(User.Role.STUDENT)
                .action(Approval.Action.SUBMITTED)
                .remarks("OD request submitted by student")
                .build();
        approvalRepository.save(approval);

        // Notify Mentor Faculty if assigned
        Faculty mentor = student.getMentorFaculty();
        if (mentor != null) {
            notificationService.createNotification(
                    mentor.getUser(),
                    "New OD Request Submitted",
                    "Student " + student.getName() + " (" + student.getRegisterNumber() + ") submitted OD request " + requestCode + ".",
                    requestCode
            );
        }

        return saved;
    }

    @Transactional
    public Request submitLeaveRequest(Long studentId, LeaveRequestDto dto, String docName, String docPath) {
        Student student = studentRepository.findById(studentId)
                .orElseThrow(() -> new IllegalArgumentException("Student not found"));

        LocalDate endDate = dto.getEndDate() != null ? dto.getEndDate() : dto.getStartDate();
        if (endDate.isBefore(dto.getStartDate())) {
            throw new IllegalArgumentException("End date cannot be earlier than start date");
        }

        long count = requestRepository.countByRequestType(Request.RequestType.LEAVE) + 1;
        String requestCode = String.format("LV-%d-%03d", LocalDate.now().getYear(), count);

        Request request = Request.builder()
                .requestCode(requestCode)
                .student(student)
                .requestType(Request.RequestType.LEAVE)
                .startDate(dto.getStartDate())
                .endDate(endDate)
                .leaveType(dto.getLeaveType())
                .reason(dto.getReason())
                .documentName(docName)
                .documentPath(docPath)
                .studentRemarks(dto.getRemarks())
                .status(Request.Status.PENDING_FACULTY)
                .attendanceUpdated(false)
                .build();

        Request saved = requestRepository.save(request);

        Approval approval = Approval.builder()
                .request(saved)
                .approver(student.getUser())
                .approverRole(User.Role.STUDENT)
                .action(Approval.Action.SUBMITTED)
                .remarks("Leave request submitted by student")
                .build();
        approvalRepository.save(approval);

        return saved;
    }

    @Transactional
    public Request facultyReview(Long requestId, User facultyUser, boolean approve, String remarks) {
        Request request = requestRepository.findById(requestId)
                .orElseThrow(() -> new IllegalArgumentException("Request not found"));

        if (request.getStatus() != Request.Status.PENDING_FACULTY) {
            throw new IllegalStateException("Request is not in PENDING_FACULTY state");
        }

        if (!approve && (remarks == null || remarks.trim().isEmpty())) {
            throw new IllegalArgumentException("Remarks are mandatory when rejecting a request");
        }

        request.setStatus(approve ? Request.Status.PENDING_HOD : Request.Status.REJECTED_FACULTY);
        request.setUpdatedAt(LocalDateTime.now());
        Request updated = requestRepository.save(request);

        Approval approval = Approval.builder()
                .request(updated)
                .approver(facultyUser)
                .approverRole(User.Role.FACULTY)
                .action(approve ? Approval.Action.FACULTY_APPROVED : Approval.Action.FACULTY_REJECTED)
                .remarks(remarks != null ? remarks : (approve ? "Recommended and forwarded to HOD" : "Rejected"))
                .build();
        approvalRepository.save(approval);

        notificationService.createNotification(
                request.getStudent().getUser(),
                "Request " + (approve ? "Approved by Faculty" : "Rejected by Faculty"),
                "Your request " + request.getRequestCode() + (approve ? " was approved by Faculty and forwarded to HOD." : " was rejected by Faculty. Remarks: " + remarks),
                request.getRequestCode()
        );

        return updated;
    }

    @Transactional
    public Request hodReview(Long requestId, User hodUser, boolean approve, String remarks) {
        Request request = requestRepository.findById(requestId)
                .orElseThrow(() -> new IllegalArgumentException("Request not found"));

        if (request.getStatus() != Request.Status.PENDING_HOD && request.getStatus() != Request.Status.PENDING_FACULTY) {
            throw new IllegalStateException("Request cannot be processed for final approval in state: " + request.getStatus());
        }

        if (!approve && (remarks == null || remarks.trim().isEmpty())) {
            throw new IllegalArgumentException("Remarks are mandatory when rejecting a request");
        }

        request.setStatus(approve ? Request.Status.APPROVED : Request.Status.REJECTED_HOD);
        request.setUpdatedAt(LocalDateTime.now());
        Request updated = requestRepository.save(request);

        Approval approval = Approval.builder()
                .request(updated)
                .approver(hodUser)
                .approverRole(User.Role.HOD_ADMIN)
                .action(approve ? Approval.Action.HOD_APPROVED : Approval.Action.HOD_REJECTED)
                .remarks(remarks != null ? remarks : (approve ? "Sanctioned by HOD" : "Rejected by HOD"))
                .build();
        approvalRepository.save(approval);

        // If approved and OD, trigger attendance integration
        if (approve && updated.getRequestType() == Request.RequestType.OD) {
            attendanceIntegrationService.integrateApprovedOdAttendance(updated);
        }

        notificationService.createNotification(
                request.getStudent().getUser(),
                "Request " + (approve ? "Approved by HOD" : "Rejected by HOD"),
                "Your request " + request.getRequestCode() + (approve ? " has received final approval from HOD." : " was rejected by HOD. Remarks: " + remarks),
                request.getRequestCode()
        );

        return updated;
    }
}
