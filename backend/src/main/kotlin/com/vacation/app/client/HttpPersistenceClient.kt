package com.vacation.app.client

import com.vacation.app.api.Activity
import com.vacation.app.api.Traveler
import com.vacation.app.api.TravelerAuthRecord
import com.vacation.app.api.TravelerCreateRequest
import com.vacation.app.api.Trip
import com.vacation.app.api.TripSummary
import org.springframework.beans.factory.annotation.Value
import org.springframework.core.ParameterizedTypeReference
import org.springframework.stereotype.Component
import org.springframework.web.reactive.function.client.WebClient
import java.util.UUID

@Component
class HttpPersistenceClient(
	builder: WebClient.Builder,
	@Value("\${services.persistence.base-url:http://localhost:8081}") baseUrl: String,
) : PersistenceClient {
	private val webClient = builder.baseUrl(baseUrl).build()

	override fun createTraveler(request: TravelerCreateRequest): Traveler =
		webClient.post().uri("/travelers").bodyValue(request).retrieve().bodyToMono(Traveler::class.java).block()!!

	override fun findTravelerAuthRecordByEmail(email: String): TravelerAuthRecord =
		webClient.get().uri { it.path("/travelers/auth-record").queryParam("email", email).build() }
			.retrieve().bodyToMono(TravelerAuthRecord::class.java).block()!!

	override fun listTrips(travelerId: UUID): List<TripSummary> =
		webClient.get().uri { it.path("/trips").queryParam("travelerId", travelerId).build() }
			.retrieve().bodyToMono(object : ParameterizedTypeReference<List<TripSummary>>() {}).block()!!

	override fun saveTrip(travelerId: UUID, trip: Trip): Trip =
		webClient.post().uri { it.path("/trips").queryParam("travelerId", travelerId).build() }
			.bodyValue(trip).retrieve().bodyToMono(Trip::class.java).block()!!

	override fun getTrip(travelerId: UUID, tripId: UUID): Trip =
		webClient.get().uri { it.path("/trips/{tripId}").queryParam("travelerId", travelerId).build(tripId) }
			.retrieve().bodyToMono(Trip::class.java).block()!!

	override fun deleteTrip(travelerId: UUID, tripId: UUID) {
		webClient.delete().uri { it.path("/trips/{tripId}").queryParam("travelerId", travelerId).build(tripId) }
			.retrieve().toBodilessEntity().block()
	}

	override fun updateActivity(tripId: UUID, dayId: UUID, activityId: UUID, activity: Activity): Activity =
		webClient.put().uri("/trips/{tripId}/days/{dayId}/activities/{activityId}", tripId, dayId, activityId)
			.bodyValue(activity).retrieve().bodyToMono(Activity::class.java).block()!!

	override fun deleteActivity(tripId: UUID, dayId: UUID, activityId: UUID) {
		webClient.delete().uri("/trips/{tripId}/days/{dayId}/activities/{activityId}", tripId, dayId, activityId)
			.retrieve().toBodilessEntity().block()
	}
}
