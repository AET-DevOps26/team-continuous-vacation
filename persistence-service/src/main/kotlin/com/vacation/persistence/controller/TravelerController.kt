package com.vacation.persistence.controller

import com.vacation.persistence.api.Traveler
import com.vacation.persistence.api.TravelerAuthRecord
import com.vacation.persistence.api.TravelerCreateRequest
import com.vacation.persistence.repository.TripTailorRepository
import jakarta.validation.Valid
import org.springframework.http.HttpStatus
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.ResponseStatus
import org.springframework.web.bind.annotation.RestController
import java.util.UUID

@RestController
@RequestMapping("/travelers")
class TravelerController(private val repository: TripTailorRepository) {
	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	fun createTraveler(@Valid @RequestBody request: TravelerCreateRequest): Traveler = repository.createTraveler(request)

	@GetMapping
	fun findTravelerByEmail(@RequestParam email: String): Traveler = repository.findTravelerByEmail(email)

	@GetMapping("/auth-record")
	fun findTravelerAuthRecordByEmail(@RequestParam email: String): TravelerAuthRecord = repository.findTravelerAuthRecordByEmail(email)

	@GetMapping("/{travelerId}")
	fun getTraveler(@PathVariable travelerId: UUID): Traveler = repository.getTraveler(travelerId)
}
