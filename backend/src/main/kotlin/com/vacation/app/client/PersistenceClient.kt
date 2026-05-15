package com.vacation.app.client

import com.vacation.app.api.Activity
import com.vacation.app.api.Traveler
import com.vacation.app.api.TravelerAuthRecord
import com.vacation.app.api.TravelerCreateRequest
import com.vacation.app.api.Trip
import com.vacation.app.api.TripSummary
import java.util.UUID

interface PersistenceClient {
	fun createTraveler(request: TravelerCreateRequest): Traveler
	fun findTravelerAuthRecordByEmail(email: String): TravelerAuthRecord
	fun listTrips(travelerId: UUID): List<TripSummary>
	fun saveTrip(travelerId: UUID, trip: Trip): Trip
	fun getTrip(travelerId: UUID, tripId: UUID): Trip
	fun deleteTrip(travelerId: UUID, tripId: UUID)
	fun updateActivity(tripId: UUID, dayId: UUID, activityId: UUID, activity: Activity): Activity
	fun deleteActivity(tripId: UUID, dayId: UUID, activityId: UUID)
}
