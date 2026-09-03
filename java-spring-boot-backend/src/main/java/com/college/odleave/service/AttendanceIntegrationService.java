package com.college.odleave.service;

import com.college.odleave.entity.Attendance;
import com.college.odleave.entity.Request;
import com.college.odleave.entity.Student;
import com.college.odleave.entity.Subject;
import com.college.odleave.repository.AttendanceRepository;
import com.college.odleave.repository.RequestRepository;
import com.college.odleave.repository.SubjectRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class AttendanceIntegrationService {

    private final AttendanceRepository attendanceRepository;
    private final RequestRepository requestRepository;
    private final SubjectRepository subjectRepository;
    private final NotificationService notificationService;

    @Transactional
    public int integrateApprovedOdAttendance(Request request) {
        if (request.getRequestType() != Request.RequestType.OD) {
            return 0;
        }

        // Idempotency check: prevent duplicate credit
        if (Boolean.TRUE.equals(request.getAttendanceUpdated())) {
            return 0;
        }

        Student student = request.getStudent();
        List<Subject> subjects = subjectRepository.findByDepartmentAndYear(student.getDepartment(), student.getYear());

        int updatedPeriods = 0;
        LocalDate current = request.getStartDate();
        LocalDate end = request.getEndDate() != null ? request.getEndDate() : request.getStartDate();

        while (!current.isAfter(end)) {
            // Exclude weekends
            if (current.getDayOfWeek() != DayOfWeek.SATURDAY && current.getDayOfWeek() != DayOfWeek.SUNDAY) {
                for (Subject subject : subjects) {
                    Optional<Attendance> existing = attendanceRepository.findByStudentIdAndSubjectIdAndAttendanceDate(
                            student.getId(), subject.getId(), current
                    );

                    Attendance record;
                    if (existing.isPresent()) {
                        record = existing.get();
                        record.setStatus(Attendance.AttendanceStatus.ON_DUTY);
                        record.setSource(Attendance.Source.OD_INTEGRATION);
                        record.setRequest(request);
                    } else {
                        record = Attendance.builder()
                                .student(student)
                                .subject(subject)
                                .attendanceDate(current)
                                .status(Attendance.AttendanceStatus.ON_DUTY)
                                .source(Attendance.Source.OD_INTEGRATION)
                                .request(request)
                                .build();
                    }
                    attendanceRepository.save(record);
                    updatedPeriods++;
                }
            }
            current = current.plusDays(1);
        }

        request.setAttendanceUpdated(true);
        requestRepository.save(request);

        // Notify student about attendance update
        notificationService.createNotification(
                student.getUser(),
                "Attendance Updated for Approved OD",
                "Your OD request " + request.getRequestCode() + " has updated " + updatedPeriods + " class periods as On-Duty credit.",
                request.getRequestCode()
        );

        return updatedPeriods;
    }
}
