package com.vacation.persistence.repository

import com.vacation.persistence.api.Activity
import com.vacation.persistence.api.ActivityTag
import com.vacation.persistence.api.ApiException
import com.vacation.persistence.api.Day
import com.vacation.persistence.api.Schedule
import com.vacation.persistence.api.TimeBlock
import com.vacation.persistence.api.Traveler
import com.vacation.persistence.api.TravelerAuthRecord
import com.vacation.persistence.api.TravelerCreateRequest
import com.vacation.persistence.api.Trip
import com.vacation.persistence.api.TripSummary
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate
import org.springframework.stereotype.Repository
import org.springframework.transaction.annotation.Transactional
import java.sql.ResultSet
import java.sql.Timestamp
import java.time.Instant
import java.time.LocalDate
import java.util.UUID

@Repository
class TripTailorRepository(private val jdbc: NamedParameterJdbcTemplate) {
	fun createTraveler(request: TravelerCreateRequest): Traveler {
		if (!request.isDemo && (request.email.isNullOrBlank() || request.passwordHash.isNullOrBlank())) {
			throw ApiException(400, "INVALID_TRAVELER", "Invalid Traveler", "Registered travelers need email and passwordHash.")
		}
		val traveler = Traveler(
			id = UUID.randomUUID(),
			email = request.email?.lowercase(),
			isDemo = request.isDemo,
			createdAt = Instant.now(),
		)
		jdbc.update(
			"""
			insert into travelers (id, email, password_hash, is_demo, created_at)
			values (:id, :email, :passwordHash, :isDemo, :createdAt)
			""".trimIndent(),
			params(
				"id" to traveler.id,
				"email" to traveler.email,
				"passwordHash" to request.passwordHash,
				"isDemo" to traveler.isDemo,
				"createdAt" to Timestamp.from(traveler.createdAt),
			),
		)
		return traveler
	}

	fun findTravelerByEmail(email: String): Traveler =
		queryTravelers("select * from travelers where email = :email", params("email" to email.lowercase()))
			.firstOrNull() ?: throw ApiException(404, "TRAVELER_NOT_FOUND", "Traveler Not Found")

	fun findTravelerAuthRecordByEmail(email: String): TravelerAuthRecord =
		jdbc.query("select * from travelers where email = :email", params("email" to email.lowercase())) { rs, _ ->
			TravelerAuthRecord(
				id = rs.uuid("id"),
				email = rs.getString("email"),
				passwordHash = rs.getString("password_hash"),
				isDemo = rs.getBoolean("is_demo"),
				createdAt = rs.getTimestamp("created_at").toInstant(),
			)
		}.firstOrNull() ?: throw ApiException(404, "TRAVELER_NOT_FOUND", "Traveler Not Found")

	fun getTraveler(id: UUID): Traveler =
		queryTravelers("select * from travelers where id = :id", params("id" to id))
			.firstOrNull() ?: throw ApiException(404, "TRAVELER_NOT_FOUND", "Traveler Not Found")

	fun listTrips(travelerId: UUID): List<TripSummary> =
		jdbc.query(
			"""
			select id, destination, start_date, end_date
			from trips
			where traveler_id = :travelerId
			order by start_date, destination
			""".trimIndent(),
			params("travelerId" to travelerId),
		) { rs, _ ->
			TripSummary(rs.uuid("id"), rs.getString("destination"), rs.localDate("start_date"), rs.localDate("end_date"))
		}

	@Transactional
	fun saveTrip(travelerId: UUID, trip: Trip): Trip {
		getTraveler(travelerId)
		jdbc.update(
			"""
			insert into trips (id, traveler_id, destination, start_date, end_date, vibe)
			values (:id, :travelerId, :destination, :startDate, :endDate, :vibe)
			""".trimIndent(),
			params(
				"id" to trip.id,
				"travelerId" to travelerId,
				"destination" to trip.destination,
				"startDate" to trip.startDate,
				"endDate" to trip.endDate,
				"vibe" to trip.vibe,
			),
		)
		trip.schedule.days.forEach { day ->
			jdbc.update(
				"insert into days (id, trip_id, day_number, date) values (:id, :tripId, :dayNumber, :date)",
				params("id" to day.id, "tripId" to trip.id, "dayNumber" to day.dayNumber, "date" to day.date),
			)
			day.activities.forEach { insertActivity(it) }
		}
		return getTrip(travelerId, trip.id)
	}

	fun getTrip(travelerId: UUID, tripId: UUID): Trip {
		val tripRows = jdbc.query(
			"select * from trips where id = :tripId and traveler_id = :travelerId",
			params("tripId" to tripId, "travelerId" to travelerId),
		) { rs, _ ->
			Trip(rs.uuid("id"), rs.getString("destination"), rs.localDate("start_date"), rs.localDate("end_date"), rs.getString("vibe"), Schedule(emptyList()))
		}
		val trip = tripRows.firstOrNull() ?: throw ApiException(404, "TRIP_NOT_FOUND", "Trip Not Found")
		return trip.copy(schedule = Schedule(daysForTrip(trip.id)))
	}

	@Transactional
	fun deleteTrip(travelerId: UUID, tripId: UUID) {
		getTrip(travelerId, tripId)
		jdbc.update("delete from trips where id = :tripId and traveler_id = :travelerId", params("tripId" to tripId, "travelerId" to travelerId))
	}

	@Transactional
	fun updateActivity(tripId: UUID, dayId: UUID, activityId: UUID, activity: Activity): Activity {
		ensureActivityExists(tripId, dayId, activityId)
		jdbc.update("delete from activity_tags where activity_id = :activityId", params("activityId" to activityId))
		jdbc.update("delete from activities where id = :activityId", params("activityId" to activityId))
		insertActivity(activity.copy(dayId = dayId))
		return getActivity(activity.id)
	}

	@Transactional
	fun deleteActivity(tripId: UUID, dayId: UUID, activityId: UUID) {
		ensureActivityExists(tripId, dayId, activityId)
		jdbc.update("delete from activities where id = :activityId", params("activityId" to activityId))
	}

	private fun insertActivity(activity: Activity) {
		jdbc.update(
			"""
			insert into activities (id, day_id, time_block, title, description, duration_minutes, is_indoor)
			values (:id, :dayId, :timeBlock, :title, :description, :durationMinutes, :isIndoor)
			""".trimIndent(),
			params(
				"id" to activity.id,
				"dayId" to activity.dayId,
				"timeBlock" to activity.timeBlock.name,
				"title" to activity.title,
				"description" to activity.description,
				"durationMinutes" to activity.durationMinutes,
				"isIndoor" to activity.isIndoor,
			),
		)
		activity.tags.orEmpty().forEach { tag ->
			jdbc.update(
				"insert into activity_tags (activity_id, tag) values (:activityId, :tag)",
				params("activityId" to activity.id, "tag" to tag.name),
			)
		}
	}

	private fun daysForTrip(tripId: UUID): List<Day> =
		jdbc.query(
			"select * from days where trip_id = :tripId order by day_number",
			params("tripId" to tripId),
		) { rs, _ ->
			Day(rs.uuid("id"), rs.getInt("day_number"), rs.localDate("date"), activitiesForDay(rs.uuid("id")))
		}

	private fun activitiesForDay(dayId: UUID): List<Activity> =
		jdbc.query(
			"select * from activities where day_id = :dayId order by time_block, title",
			params("dayId" to dayId),
		) { rs, _ -> activityFrom(rs) }

	private fun getActivity(activityId: UUID): Activity =
		jdbc.query("select * from activities where id = :activityId", params("activityId" to activityId)) { rs, _ -> activityFrom(rs) }
			.firstOrNull() ?: throw ApiException(404, "ACTIVITY_NOT_FOUND", "Activity Not Found")

	private fun activityFrom(rs: ResultSet): Activity {
		val activityId = rs.uuid("id")
		val tags = jdbc.query(
			"select tag from activity_tags where activity_id = :activityId order by tag",
			params("activityId" to activityId),
		) { tagRs, _ -> ActivityTag.valueOf(tagRs.getString("tag")) }
		val indoor = rs.getObject("is_indoor") as Boolean?
		return Activity(
			id = activityId,
			dayId = rs.uuid("day_id"),
			timeBlock = TimeBlock.valueOf(rs.getString("time_block")),
			title = rs.getString("title"),
			description = rs.getString("description"),
			durationMinutes = rs.getInt("duration_minutes"),
			isIndoor = indoor,
			tags = tags,
		)
	}

	private fun ensureActivityExists(tripId: UUID, dayId: UUID, activityId: UUID) {
		val count = jdbc.queryForObject(
			"""
			select count(*)
			from activities a
			join days d on d.id = a.day_id
			where a.id = :activityId and d.id = :dayId and d.trip_id = :tripId
			""".trimIndent(),
			params("tripId" to tripId, "dayId" to dayId, "activityId" to activityId),
			Int::class.java,
		) ?: 0
		if (count == 0) throw ApiException(404, "ACTIVITY_NOT_FOUND", "Activity Not Found")
	}

	private fun queryTravelers(sql: String, params: MapSqlParameterSource): List<Traveler> =
		jdbc.query(sql, params) { rs, _ ->
			Traveler(
				id = rs.uuid("id"),
				email = rs.getString("email"),
				isDemo = rs.getBoolean("is_demo"),
				createdAt = rs.getTimestamp("created_at").toInstant(),
			)
		}

	private fun params(vararg pairs: Pair<String, Any?>): MapSqlParameterSource =
		pairs.fold(MapSqlParameterSource()) { source, pair -> source.addValue(pair.first, pair.second) }

	private fun ResultSet.uuid(column: String): UUID = getObject(column, UUID::class.java)
	private fun ResultSet.localDate(column: String): LocalDate = getObject(column, LocalDate::class.java)
}
