package com.college.odleave.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.*;
import java.time.LocalDate;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class OdRequestDto {
    @NotBlank(message = "Event name is required")
    private String eventName;

    @NotBlank(message = "Event type is required")
    private String eventType;

    @NotNull(message = "Start date is required")
    private LocalDate startDate;

    private LocalDate endDate;

    @NotBlank(message = "Venue is required")
    private String venue;

    @NotBlank(message = "Reason is required")
    private String reason;

    private String remarks;
}
