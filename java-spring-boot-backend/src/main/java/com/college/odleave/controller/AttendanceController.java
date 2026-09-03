package com.college.odleave.controller;

import com.college.odleave.entity.Attendance;
import com.college.odleave.repository.AttendanceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/attendance")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class AttendanceController {

    private final AttendanceRepository attendanceRepository;

    @GetMapping("/student/{studentId}")
    public ResponseEntity<?> getStudentAttendance(@PathVariable Long studentId) {
        List<Attendance> history = attendanceRepository.findByStudentIdOrderByAttendanceDateDesc(studentId);
        return ResponseEntity.ok(Map.of("attendanceHistory", history));
    }
}
