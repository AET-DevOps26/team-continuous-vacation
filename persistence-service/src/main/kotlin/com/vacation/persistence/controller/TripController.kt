package com.vacation.persistence.controller

import com.vacation.persistence.api.Activity
import com.vacation.persistence.api.Trip
import com.vacation.persistence.api.TripSummary
import com.vacation.persistence.repository.TripTailorRepository
import org.springframework.http.HttpStatus
import org.springframework.web.bind.annotation.DeleteMapping
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.PutMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.ResponseStatus
import org.springframework.web.bind.annotation.RestController
import java.util.UUID

@RestController
@RequestMapping
class TripController(private val repository: TripTailorRepository) {
	@GetMapping("/trips")
	fun listTrips(@RequestParam travelerId: UUID): List<TripSummary> = repository.listTrips(travelerId)

	@PostMapping("/trips")
	@ResponseStatus(HttpStatus.CREATED)
	fun saveTrip(@RequestParam travelerId: UUID, @RequestBody trip: Trip): Trip = repository.saveTrip(travelerId, trip)

	@GetMapping("/trips/{tripId}")
	fun getTrip(@RequestParam travelerId: UUID, @PathVariable tripId: UUID): Trip = repository.getTrip(travelerId, tripId)

	@DeleteMapping("/trips/{tripId}")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	fun deleteTrip(@RequestParam travelerId: UUID, @PathVariable tripId: UUID) = repository.deleteTrip(travelerId, tripId)

	@PutMapping("/trips/{tripId}/days/{dayId}/activities/{activityId}")
	fun updateActivity(
		@PathVariable tripId: UUID,
		@PathVariable dayId: UUID,
		@PathVariable activityId: UUID,
		@RequestBody activity: Activity,
	): Activity = repository.updateActivity(tripId, dayId, activityId, activity)

	@DeleteMapping("/trips/{tripId}/days/{dayId}/activities/{activityId}")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	fun deleteActivity(
		@PathVariable tripId: UUID,
		@PathVariable dayId: UUID,
		@PathVariable activityId: UUID,
	) = repository.deleteActivity(tripId, dayId, activityId)
}
