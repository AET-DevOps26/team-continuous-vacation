package com.vacation.app

import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.bind.annotation.CrossOrigin
import java.time.LocalDateTime
import org.springframework.web.bind.annotation.RequestParam

data class Vacation(
    val id: Int,
    val name: String,
    val destination: String,
    val startTime: LocalDateTime,
    val endTime: LocalDateTime
)

@RestController
@CrossOrigin(origins = ["*"])
class HelloController {

    @GetMapping("/hello")
    fun sayHello(): String {
        return "Hello from the TripTailor Backend!"
    }

    @GetMapping("/vacations")
    fun getMockVacations(
        @RequestParam(required = false) _start: Int?,
        @RequestParam(required = false) _end: Int?
    ): List<Vacation> {
        return listOf(
            Vacation(
                id = 1,
                name = "Alpine Skiing",
                destination = "Zermatt, Switzerland",
                startTime = LocalDateTime.of(2026, 12, 20, 9, 0),
                endTime = LocalDateTime.of(2026, 12, 27, 18, 0)
            ),
            Vacation(
                id = 2,
                name = "Tropical Retreat",
                destination = "Bali, Indonesia",
                startTime = LocalDateTime.of(2026, 6, 10, 10, 30),
                endTime = LocalDateTime.of(2026, 6, 25, 20, 0)
            ),
            Vacation(
                id = 3,
                name = "City Exploration",
                destination = "Tokyo, Japan",
                startTime = LocalDateTime.of(2026, 9, 5, 8, 0),
                endTime = LocalDateTime.of(2026, 9, 15, 22, 0)
            )
        )
    }
}
