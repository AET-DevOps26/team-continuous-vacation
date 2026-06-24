package com.vacation.app

import com.jayway.jsonpath.JsonPath
import com.vacation.app.api.Activity
import com.vacation.app.api.ActivityTag
import com.vacation.app.api.Day
import com.vacation.app.api.GenerationPreferences
import com.vacation.app.api.Traveler
import com.vacation.app.api.TravelerAuthRecord
import com.vacation.app.api.TravelerCreateRequest
import com.vacation.app.api.Trip
import com.vacation.app.api.TripSummary
import com.vacation.app.api.RegenerationInstruction
import com.vacation.app.api.Schedule
import com.vacation.app.api.TimeBlock
import com.vacation.app.client.GenAiClient
import com.vacation.app.client.PersistenceClient
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.test.context.TestConfiguration
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Primary
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.http.HttpHeaders
import org.springframework.http.MediaType
import org.springframework.test.context.junit.jupiter.SpringExtension
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.delete
import org.springframework.test.web.servlet.get
import org.springframework.test.web.servlet.patch
import org.springframework.test.web.servlet.post
import org.springframework.web.reactive.function.client.WebClientResponseException
import java.time.Instant
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import org.junit.jupiter.api.extension.ExtendWith

@ExtendWith(SpringExtension::class)
@SpringBootTest
@AutoConfigureMockMvc
class AppApiE2ETest {
	@Autowired
	private lateinit var mockMvc: MockMvc

	@Autowired
	private lateinit var persistenceClient: PersistenceClient

	@Test
	fun `health endpoint returns service status`() {
		mockMvc.get("/health")
			.andExpect {
				status { isOk() }
				jsonPath("$.status") { value("UP") }
			}
	}

	@Test
	fun `home page serves interactive openapi documentation`() {
		mockMvc.get("/")
			.andExpect {
				status { isOk() }
				content { string(org.hamcrest.Matchers.containsString("SwaggerUIBundle")) }
				content { string(org.hamcrest.Matchers.containsString("TripTailor App API")) }
				content { string(org.hamcrest.Matchers.containsString("triptailorAccessToken")) }
				content { string(org.hamcrest.Matchers.containsString("requestInterceptor: attachStoredToken")) }
			}

		mockMvc.get("/openapi.yaml")
			.andExpect {
				status { isOk() }
				content { string(org.hamcrest.Matchers.containsString("title: TripTailor — App API")) }
				content { string(org.hamcrest.Matchers.containsString("Public-facing Backend-for-Frontend")) }
				content { string(org.hamcrest.Matchers.containsString("/health:")) }
				content { string(org.hamcrest.Matchers.containsString("bearerAuth:")) }
			}
	}

	@Test
	fun `demo traveler can create fetch update and delete a trip`() {
		val authJson = mockMvc.post("/auth/demo").andExpect { status { isCreated() } }.andReturn().response.contentAsString
		val travelerId = JsonPath.read<String>(authJson, "$.travelerId")
		val accessToken = JsonPath.read<String>(authJson, "$.accessToken")

		val tripJson = mockMvc.post("/trips") {
			header("Authorization", "Bearer $accessToken")
			contentType = MediaType.APPLICATION_JSON
			content = """{"destination":"Munich","startDate":"2026-05-15","endDate":"2026-05-16","vibe":"Sporty"}"""
		}.andExpect {
			status { isCreated() }
			jsonPath("$.destination") { value("Munich") }
			jsonPath("$.schedule.days.length()") { value(2) }
			jsonPath("$.schedule.days[0].activities[0].title") { value("AI Munich Sporty plan") }
		}.andReturn().response.contentAsString

		val tripId = JsonPath.read<String>(tripJson, "$.id")
		val dayId = JsonPath.read<String>(tripJson, "$.schedule.days[0].id")
		val activityId = JsonPath.read<String>(tripJson, "$.schedule.days[0].activities[0].id")

		mockMvc.get("/trips/$tripId") { header("Authorization", "Bearer $accessToken") }
			.andExpect { status { isOk() } }

		mockMvc.patch("/trips/$tripId/days/$dayId/activities/$activityId") {
			header("Authorization", "Bearer $accessToken")
			contentType = MediaType.APPLICATION_JSON
			content = """{"instruction":"Make this indoor"}"""
		}.andExpect {
			status { isOk() }
			jsonPath("$.title") { value("AI indoor climbing session") }
			jsonPath("$.isIndoor") { value(true) }
		}

		mockMvc.delete("/trips/$tripId") { header("Authorization", "Bearer $accessToken") }
			.andExpect { status { isNoContent() } }

		assertEquals(emptyList<TripSummary>(), persistenceClient.listTrips(UUID.fromString(travelerId)))
	}

	@Test
	fun `trips require bearer token`() {
		mockMvc.get("/trips")
			.andExpect {
				status { isUnauthorized() }
				jsonPath("$.type") { value("UNAUTHORIZED") }
			}
	}

	@Test
	fun `invalid bearer token is rejected`() {
		mockMvc.get("/trips") {
			header("Authorization", "Bearer not-a-jwt")
		}.andExpect {
			status { isUnauthorized() }
		}
	}

	@Test
	fun `registered traveler can login and invalid credentials are rejected`() {
		val email = "ada-${UUID.randomUUID()}@example.com"
		mockMvc.post("/auth/register") {
			contentType = MediaType.APPLICATION_JSON
			content = """{"email":"$email","password":"password123"}"""
		}.andExpect {
			status { isCreated() }
			jsonPath("$.accessToken") { exists() }
			jsonPath("$.isDemo") { value(false) }
		}

		mockMvc.post("/auth/login") {
			contentType = MediaType.APPLICATION_JSON
			content = """{"email":"$email","password":"password123"}"""
		}.andExpect {
			status { isOk() }
			jsonPath("$.accessToken") { exists() }
		}

		mockMvc.post("/auth/login") {
			contentType = MediaType.APPLICATION_JSON
			content = """{"email":"$email","password":"wrong-password"}"""
		}.andExpect {
			status { isUnauthorized() }
			jsonPath("$.type") { value("INVALID_CREDENTIALS") }
		}
	}

	@Test
	fun `duplicate registration maps to conflict`() {
		val email = "duplicate-${UUID.randomUUID()}@example.com"
		repeat(2) { attempt ->
			mockMvc.post("/auth/register") {
				contentType = MediaType.APPLICATION_JSON
				content = """{"email":"$email","password":"password123"}"""
			}.andExpect {
				if (attempt == 0) {
					status { isCreated() }
				} else {
					status { isConflict() }
					jsonPath("$.type") { value("EMAIL_ALREADY_REGISTERED") }
				}
			}
		}
	}

	@Test
	fun `traveler cannot access another travelers trip`() {
		val firstToken = JsonPath.read<String>(
			mockMvc.post("/auth/demo").andExpect { status { isCreated() } }.andReturn().response.contentAsString,
			"$.accessToken",
		)
		val secondToken = JsonPath.read<String>(
			mockMvc.post("/auth/demo").andExpect { status { isCreated() } }.andReturn().response.contentAsString,
			"$.accessToken",
		)
		val tripJson = mockMvc.post("/trips") {
			header("Authorization", "Bearer $firstToken")
			contentType = MediaType.APPLICATION_JSON
			content = """{"destination":"Vienna","startDate":"2026-07-01","endDate":"2026-07-01","vibe":"Historic"}"""
		}.andExpect { status { isCreated() } }.andReturn().response.contentAsString
		val tripId = JsonPath.read<String>(tripJson, "$.id")

		mockMvc.get("/trips/$tripId") {
			header("Authorization", "Bearer $secondToken")
		}.andExpect {
			status { isNotFound() }
			jsonPath("$.type") { value("NOT_FOUND") }
		}
	}

	@Test
	fun `invalid dates are rejected before GenAI call`() {
		val token = JsonPath.read<String>(
			mockMvc.post("/auth/demo").andExpect { status { isCreated() } }.andReturn().response.contentAsString,
			"$.accessToken",
		)

		mockMvc.post("/trips") {
			header("Authorization", "Bearer $token")
			contentType = MediaType.APPLICATION_JSON
			content = """{"destination":"Munich","startDate":"2026-08-03","endDate":"2026-08-01","vibe":"Sporty"}"""
		}.andExpect {
			status { isBadRequest() }
			jsonPath("$.type") { value("INVALID_DATES") }
		}
	}

	@Test
	fun `GenAI upstream failure maps to upstream error`() {
		val token = JsonPath.read<String>(
			mockMvc.post("/auth/demo").andExpect { status { isCreated() } }.andReturn().response.contentAsString,
			"$.accessToken",
		)

		mockMvc.post("/trips") {
			header("Authorization", "Bearer $token")
			contentType = MediaType.APPLICATION_JSON
			content = """{"destination":"GenAI down","startDate":"2026-09-01","endDate":"2026-09-01","vibe":"Sporty"}"""
		}.andExpect {
			status { isBadGateway() }
			jsonPath("$.type") { value("UPSTREAM_ERROR") }
		}
	}

	@TestConfiguration
	class FakePersistenceConfiguration {
		@Bean
		@Primary
		fun fakePersistenceClient(): PersistenceClient = InMemoryPersistenceClient()

		@Bean
		@Primary
		fun fakeGenAiClient(): GenAiClient = FakeGenAiClient()
	}
}

private class FakeGenAiClient : GenAiClient {
	override fun generateSchedule(preferences: GenerationPreferences): Schedule {
		if (preferences.destination == "GenAI down") {
			throw WebClientResponseException.BadGateway.create(502, "Bad Gateway", HttpHeaders.EMPTY, ByteArray(0), null)
		}
		val days = generateSequence(preferences.startDate) { it.plusDays(1) }
			.takeWhile { !it.isAfter(preferences.endDate) }
			.mapIndexed { index, date ->
				val dayId = UUID.randomUUID()
				Day(
					id = dayId,
					dayNumber = index + 1,
					date = date,
					activities = listOf(
						Activity(
							id = UUID.randomUUID(),
							dayId = dayId,
							timeBlock = TimeBlock.MORNING,
							title = "AI ${preferences.destination} ${preferences.vibe} plan",
							description = "Generated by the fake GenAI client for backend E2E tests.",
							durationMinutes = 90,
							isIndoor = false,
							tags = listOf(ActivityTag.OUTDOOR),
						),
					),
				)
			}
			.toList()

		return Schedule(days)
	}

	override fun suggestAlternative(
		instruction: RegenerationInstruction,
		activity: Activity,
		tripContext: Trip,
	): Activity =
		Activity(
			id = UUID.randomUUID(),
			dayId = activity.dayId,
			timeBlock = TimeBlock.AFTERNOON,
			title = "AI indoor climbing session",
			description = "Generated for instruction: ${instruction.instruction}",
			durationMinutes = 120,
			isIndoor = true,
			tags = listOf(ActivityTag.INDOOR, ActivityTag.SPORTY),
		)
}

private class InMemoryPersistenceClient : PersistenceClient {
	private val travelers = ConcurrentHashMap<UUID, Traveler>()
	private val authRecords = ConcurrentHashMap<String, TravelerAuthRecord>()
	private val trips = ConcurrentHashMap<UUID, MutableMap<UUID, Trip>>()

	override fun createTraveler(request: TravelerCreateRequest): Traveler {
		if (!request.email.isNullOrBlank() && authRecords.containsKey(request.email)) {
			throw WebClientResponseException.Conflict.create(409, "Conflict", HttpHeaders.EMPTY, ByteArray(0), null)
		}
		val traveler = Traveler(UUID.randomUUID(), request.email, request.isDemo, Instant.now())
		travelers[traveler.id] = traveler
		if (!request.email.isNullOrBlank() && !request.passwordHash.isNullOrBlank()) {
			authRecords[request.email] = TravelerAuthRecord(traveler.id, request.email, request.passwordHash, traveler.isDemo, traveler.createdAt)
		}
		trips[traveler.id] = ConcurrentHashMap()
		return traveler
	}

	override fun findTravelerAuthRecordByEmail(email: String): TravelerAuthRecord =
		authRecords[email] ?: throw WebClientResponseException.NotFound.create(404, "Not Found", HttpHeaders.EMPTY, ByteArray(0), null)

	override fun listTrips(travelerId: UUID): List<TripSummary> =
		trips[travelerId].orEmpty().values.map { TripSummary(it.id, it.destination, it.startDate, it.endDate) }

	override fun saveTrip(travelerId: UUID, trip: Trip): Trip {
		val travelerTrips = trips[travelerId] ?: throw WebClientResponseException.NotFound.create(404, "Not Found", HttpHeaders.EMPTY, ByteArray(0), null)
		travelerTrips[trip.id] = trip
		return trip
	}

	override fun getTrip(travelerId: UUID, tripId: UUID): Trip =
		trips[travelerId]?.get(tripId) ?: throw WebClientResponseException.NotFound.create(404, "Not Found", HttpHeaders.EMPTY, ByteArray(0), null)

	override fun deleteTrip(travelerId: UUID, tripId: UUID) {
		val travelerTrips = trips[travelerId] ?: throw WebClientResponseException.NotFound.create(404, "Not Found", HttpHeaders.EMPTY, ByteArray(0), null)
		if (travelerTrips.remove(tripId) == null) {
			throw WebClientResponseException.NotFound.create(404, "Not Found", HttpHeaders.EMPTY, ByteArray(0), null)
		}
	}

	override fun updateActivity(tripId: UUID, dayId: UUID, activityId: UUID, activity: Activity): Activity {
		val travelerTrips = trips.values.first { it.containsKey(tripId) }
		val trip = travelerTrips.getValue(tripId)
		val days = trip.schedule.days.map { day ->
			if (day.id == dayId) day.copy(activities = day.activities.map { if (it.id == activityId) activity else it }) else day
		}
		travelerTrips[tripId] = trip.copy(schedule = trip.schedule.copy(days = days))
		return activity
	}

	override fun deleteActivity(tripId: UUID, dayId: UUID, activityId: UUID) {
		val travelerTrips = trips.values.first { it.containsKey(tripId) }
		val trip = travelerTrips.getValue(tripId)
		val days = trip.schedule.days.map { day ->
			if (day.id == dayId) day.copy(activities = day.activities.filterNot { it.id == activityId }) else day
		}
		travelerTrips[tripId] = trip.copy(schedule = trip.schedule.copy(days = days))
	}
}
