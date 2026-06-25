package com.vacation.app.service

import com.vacation.app.api.Activity
import com.vacation.app.api.ApiException
import com.vacation.app.api.GenerationPreferences
import com.vacation.app.api.RegenerationInstruction
import com.vacation.app.api.Trip
import com.vacation.app.api.TripSummary
import com.vacation.app.client.GenAiClient
import com.vacation.app.client.PersistenceClient
import io.micrometer.core.instrument.MeterRegistry
import io.micrometer.observation.Observation
import io.micrometer.observation.ObservationRegistry
import org.springframework.stereotype.Service
import java.util.UUID

@Service
class TripService(
	private val persistenceClient: PersistenceClient,
	private val genAiClient: GenAiClient,
	private val observationRegistry: ObservationRegistry,
	private val meterRegistry: MeterRegistry,
) {
	fun listTrips(travelerId: UUID): List<TripSummary> = persistenceClient.listTrips(travelerId)

	fun generateTrip(travelerId: UUID, preferences: GenerationPreferences): Trip =
		Observation.createNotStarted("trip.generate", observationRegistry)
			.lowCardinalityKeyValue("trip.destination", preferences.destination)
			.lowCardinalityKeyValue("trip.vibe", preferences.vibe)
			.observeReturning {
				generateTripObserved(travelerId, preferences)
			}

	private fun generateTripObserved(travelerId: UUID, preferences: GenerationPreferences): Trip {
		return try {
			if (preferences.endDate.isBefore(preferences.startDate)) {
				throw ApiException(400, "INVALID_DATES", "Invalid Dates", "endDate must be on or after startDate.")
			}
			val trip = Trip(
				id = UUID.randomUUID(),
				destination = preferences.destination,
				startDate = preferences.startDate,
				endDate = preferences.endDate,
				vibe = preferences.vibe,
				schedule = genAiClient.generateSchedule(preferences),
			)
			persistenceClient.saveTrip(travelerId, trip).also {
				recordCounter("triptailor.trips.generated", "success")
			}
		} catch (exception: RuntimeException) {
			recordCounter("triptailor.trips.generated", "error")
			throw exception
		}
	}

	fun getTrip(travelerId: UUID, tripId: UUID): Trip = persistenceClient.getTrip(travelerId, tripId)

	fun deleteTrip(travelerId: UUID, tripId: UUID) = persistenceClient.deleteTrip(travelerId, tripId)

	fun regenerateActivity(
		travelerId: UUID,
		tripId: UUID,
		dayId: UUID,
		activityId: UUID,
		instruction: RegenerationInstruction,
	): Activity =
		Observation.createNotStarted("trip.regenerate_activity", observationRegistry)
			.observeReturning {
				regenerateActivityObserved(travelerId, tripId, dayId, activityId, instruction)
			}

	private fun regenerateActivityObserved(
		travelerId: UUID,
		tripId: UUID,
		dayId: UUID,
		activityId: UUID,
		instruction: RegenerationInstruction,
	): Activity {
		return try {
			val trip = persistenceClient.getTrip(travelerId, tripId)
			val activity = trip.schedule.days
				.firstOrNull { it.id == dayId }
				?.activities
				?.firstOrNull { it.id == activityId }
				?: throw ApiException(404, "ACTIVITY_NOT_FOUND", "Activity Not Found")

			val replacement = genAiClient.suggestAlternative(instruction, activity, trip).copy(dayId = dayId)
			persistenceClient.updateActivity(tripId, dayId, activityId, replacement).also {
				recordCounter("triptailor.activity.regenerations", "success")
			}
		} catch (exception: RuntimeException) {
			recordCounter("triptailor.activity.regenerations", "error")
			throw exception
		}
	}

	fun deleteActivity(travelerId: UUID, tripId: UUID, dayId: UUID, activityId: UUID) {
		persistenceClient.getTrip(travelerId, tripId)
		persistenceClient.deleteActivity(tripId, dayId, activityId)
	}

	private fun <T> Observation.observeReturning(block: () -> T): T {
		start()
		return try {
			openScope().use {
				block()
			}
		} catch (exception: RuntimeException) {
			error(exception)
			throw exception
		} finally {
			stop()
		}
	}

	private fun recordCounter(name: String, outcome: String) {
		meterRegistry.counter(name, "outcome", outcome).increment()
	}
}
