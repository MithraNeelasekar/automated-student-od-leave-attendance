package com.college.odleave.controller;

import com.college.odleave.dto.ReviewDto;
import com.college.odleave.entity.Request;
import com.college.odleave.entity.User;
import com.college.odleave.repository.FacultyRepository;
import com.college.odleave.repository.RequestRepository;
import com.college.odleave.repository.StudentRepository;
import com.college.odleave.repository.UserRepository;
import com.college.odleave.service.RequestService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class AdminController {

    private final RequestRepository requestRepository;
    private final StudentRepository studentRepository;
    private final FacultyRepository facultyRepository;
    private final UserRepository userRepository;
    private final RequestService requestService;

    @GetMapping("/dashboard")
    public ResponseEntity<?> getDashboardStats() {
        return ResponseEntity.ok(Map.of(
                "totalStudents", studentRepository.count(),
                "totalFaculty", facultyRepository.count(),
                "totalRequests", requestRepository.count(),
                "approvedRequests", requestRepository.countByRequestType(Request.RequestType.OD)
        ));
    }

    @GetMapping("/requests")
    public ResponseEntity<?> getAllRequests() {
        List<Request> all = requestRepository.findAll();
        return ResponseEntity.ok(Map.of("requests", all));
    }

    @PutMapping("/requests/{id}/approve")
    public ResponseEntity<?> approveRequest(@PathVariable Long id,
                                           @RequestParam Long hodUserId,
                                           @RequestBody(required = false) ReviewDto reviewDto) {
        User user = userRepository.findById(hodUserId).orElseThrow();
        String remarks = (reviewDto != null && reviewDto.getRemarks() != null) ? reviewDto.getRemarks() : "Sanctioned by HOD";
        Request updated = requestService.hodReview(id, user, true, remarks);
        return ResponseEntity.ok(Map.of("message", "Final approval granted & attendance integrated", "request", updated));
    }

    @PutMapping("/requests/{id}/reject")
    public ResponseEntity<?> rejectRequest(@PathVariable Long id,
                                          @RequestParam Long hodUserId,
                                          @RequestBody ReviewDto reviewDto) {
        User user = userRepository.findById(hodUserId).orElseThrow();
        String remarks = (reviewDto != null) ? reviewDto.getRemarks() : "";
        Request updated = requestService.hodReview(id, user, false, remarks);
        return ResponseEntity.ok(Map.of("message", "Request rejected by HOD", "request", updated));
    }
}
