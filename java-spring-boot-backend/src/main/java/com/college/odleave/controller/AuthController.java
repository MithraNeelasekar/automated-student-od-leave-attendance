package com.college.odleave.controller;

import com.college.odleave.dto.AuthResponse;
import com.college.odleave.dto.LoginRequest;
import com.college.odleave.entity.User;
import com.college.odleave.repository.UserRepository;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class AuthController {

    private final UserRepository userRepository;

    @PostMapping("/login")
    public ResponseEntity<?> login(@Valid @RequestBody LoginRequest loginRequest) {
        User user = userRepository.findByUsername(loginRequest.getUsername())
                .or(() -> userRepository.findByEmail(loginRequest.getUsername()))
                .orElse(null);

        if (user == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(Map.of("error", "Invalid username or password"));
        }

        if (loginRequest.getRole() != null && !loginRequest.getRole().isEmpty() &&
            !user.getRole().name().equalsIgnoreCase(loginRequest.getRole())) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN)
                    .body(Map.of("error", "Role mismatch for this account"));
        }

        String mockToken = "jwt-token-" + user.getUsername() + "-" + System.currentTimeMillis();

        AuthResponse response = AuthResponse.builder()
                .token(mockToken)
                .id(user.getId())
                .username(user.getUsername())
                .role(user.getRole().name())
                .email(user.getEmail())
                .fullName(user.getFullName())
                .build();

        return ResponseEntity.ok(Map.of("token", mockToken, "user", response));
    }

    @PostMapping("/forgot-password")
    public ResponseEntity<?> forgotPassword(@RequestBody Map<String, String> payload) {
        String email = payload.get("email");
        return ResponseEntity.ok(Map.of(
                "message", "Password reset instructions sent to " + email,
                "demo_hint", "Demo password for all accounts: password123"
        ));
    }
}
