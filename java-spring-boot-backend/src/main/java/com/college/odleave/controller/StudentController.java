package com.college.odleave.controller;

import com.college.odleave.dto.LeaveRequestDto;
import com.college.odleave.dto.OdRequestDto;
import com.college.odleave.entity.Request;
import com.college.odleave.entity.Student;
import com.college.odleave.repository.RequestRepository;
import com.college.odleave.repository.StudentRepository;
import com.college.odleave.service.RequestService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class StudentController {

    private final StudentRepository studentRepository;
    private final RequestRepository requestRepository;
    private final RequestService requestService;

    @GetMapping("/students/{id}")
    public ResponseEntity<?> getStudentProfile(@PathVariable Long id) {
        Student student = studentRepository.findById(id).orElse(null);
        if (student == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("error", "Student not found"));
        }
        return ResponseEntity.ok(Map.of("student", student));
    }

    @PostMapping("/requests/od")
    public ResponseEntity<?> applyOd(@RequestParam Long studentId,
                                     @Valid @RequestBody OdRequestDto dto) {
        try {
            Request created = requestService.submitOdRequest(studentId, dto, "supporting_proof.pdf", "/uploads/sample_cert.pdf");
            return ResponseEntity.status(HttpStatus.CREATED).body(created);
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @PostMapping("/requests/leave")
    public ResponseEntity<?> applyLeave(@RequestParam Long studentId,
                                        @Valid @RequestBody LeaveRequestDto dto) {
        try {
            Request created = requestService.submitLeaveRequest(studentId, dto, "leave_document.pdf", "/uploads/sample_cert.pdf");
            return ResponseEntity.status(HttpStatus.CREATED).body(created);
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/requests/student/{studentId}")
    public ResponseEntity<?> getStudentRequests(@PathVariable Long studentId) {
        List<Request> list = requestRepository.findByStudentIdOrderByCreatedAtDesc(studentId);
        return ResponseEntity.ok(Map.of("requests", list));
    }
}
