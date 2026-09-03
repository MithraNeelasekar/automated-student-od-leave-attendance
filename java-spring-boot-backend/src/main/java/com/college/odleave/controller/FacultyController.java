package com.college.odleave.controller;

import com.college.odleave.dto.ReviewDto;
import com.college.odleave.entity.Request;
import com.college.odleave.entity.User;
import com.college.odleave.repository.RequestRepository;
import com.college.odleave.repository.UserRepository;
import com.college.odleave.service.RequestService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/faculty")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class FacultyController {

    private final RequestRepository requestRepository;
    private final RequestService requestService;
    private final UserRepository userRepository;

    @GetMapping("/requests/pending")
    public ResponseEntity<?> getPendingRequests() {
        List<Request> pending = requestRepository.findByStatusOrderByCreatedAtAsc(Request.Status.PENDING_FACULTY);
        return ResponseEntity.ok(Map.of("requests", pending));
    }

    @PutMapping("/requests/{id}/approve")
    public ResponseEntity<?> approveRequest(@PathVariable Long id,
                                           @RequestParam Long facultyUserId,
                                           @RequestBody(required = false) ReviewDto reviewDto) {
        User user = userRepository.findById(facultyUserId).orElseThrow();
        String remarks = (reviewDto != null && reviewDto.getRemarks() != null) ? reviewDto.getRemarks() : "Recommended to HOD";
        Request updated = requestService.facultyReview(id, user, true, remarks);
        return ResponseEntity.ok(Map.of("message", "Request approved and forwarded to HOD", "request", updated));
    }

    @PutMapping("/requests/{id}/reject")
    public ResponseEntity<?> rejectRequest(@PathVariable Long id,
                                          @RequestParam Long facultyUserId,
                                          @RequestBody ReviewDto reviewDto) {
        User user = userRepository.findById(facultyUserId).orElseThrow();
        String remarks = (reviewDto != null) ? reviewDto.getRemarks() : "";
        Request updated = requestService.facultyReview(id, user, false, remarks);
        return ResponseEntity.ok(Map.of("message", "Request rejected", "request", updated));
    }
}
