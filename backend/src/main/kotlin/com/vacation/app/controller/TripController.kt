package com.vacation.app.controller

import com.vacation.app.api.Activity
import com.vacation.app.api.GenerationPreferences
import com.vacation.app.api.RegenerationInstruction
import com.vacation.app.api.Trip
import com.vacation.app.api.TripSummary
import com.vacation.app.service.TripService
import jakarta.validation.Valid
import org.springframework.http.HttpStatus
import org.springframework.security.core.annotation.AuthenticationPrincipal
import org.springframework.security.oauth2.jwt.Jwt
import org.springframework.web.bind.annotation.DeleteMapping
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PatchMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.ResponseStatus
import org.springframework.web.bind.annotation.RestController
import java.util.UUID

@RestController
@RequestMapping("/trips")
class TripController(private val tripService: TripService) {
	@GetMapping
	fun listTrips(@AuthenticationPrincipal jwt: Jwt): List<TripSummary> = tripService.listTrips(jwt.travelerId())

	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	fun generateTrip(
		@AuthenticationPrincipal jwt: Jwt,
		@Valid @RequestBody request: GenerationPreferences,
	): Trip = tripService.generateTrip(jwt.travelerId(), request)

	@GetMapping("/{tripId}")
	fun getTrip(
		@AuthenticationPrincipal jwt: Jwt,
		@PathVariable tripId: UUID,
	): Trip = tripService.getTrip(jwt.travelerId(), tripId)

	@DeleteMapping("/{tripId}")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	fun deleteTrip(
		@AuthenticationPrincipal jwt: Jwt,
		@PathVariable tripId: UUID,
	) = tripService.deleteTrip(jwt.travelerId(), tripId)

	@PatchMapping("/{tripId}/days/{dayId}/activities/{activityId}")
	fun regenerateActivity(
		@AuthenticationPrincipal jwt: Jwt,
		@PathVariable tripId: UUID,
		@PathVariable dayId: UUID,
		@PathVariable activityId: UUID,
		@Valid @RequestBody request: RegenerationInstruction,
	): Activity = tripService.regenerateActivity(jwt.travelerId(), tripId, dayId, activityId, request)

	@DeleteMapping("/{tripId}/days/{dayId}/activities/{activityId}")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	fun deleteActivity(
		@AuthenticationPrincipal jwt: Jwt,
		@PathVariable tripId: UUID,
		@PathVariable dayId: UUID,
		@PathVariable activityId: UUID,
	) = tripService.deleteActivity(jwt.travelerId(), tripId, dayId, activityId)

	private fun Jwt.travelerId(): UUID = UUID.fromString(subject)
}
