package com.vacation.app

import com.jayway.jsonpath.JsonPath
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpServer
import com.vacation.app.api.Activity
import com.vacation.app.api.ActivityTag
import com.vacation.app.api.Day
import com.vacation.app.api.GenerationPreferences
import com.vacation.app.api.RegenerationInstruction
import com.vacation.app.api.Schedule
import com.vacation.app.api.TimeBlock
import com.vacation.app.api.TravelerCreateRequest
import com.vacation.app.api.Trip
import com.vacation.app.client.HttpGenAiClient
import com.vacation.app.client.HttpPersistenceClient
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.springframework.web.reactive.function.client.WebClient
import java.net.InetSocketAddress
import java.time.LocalDate
import java.util.UUID

class HttpClientTests {
	@Test
	fun `genai client posts schedule preferences and maps schedule response`() {
		RecordingHttpServer().use { server ->
			server.enqueueJson(
				"""
				{
				  "days": [
				    {
				      "id": "00000000-0000-0000-0000-000000000101",
				      "dayNumber": 1,
				      "date": "2026-07-10",
				      "activities": [
				        {
				          "id": "00000000-0000-0000-0000-000000000201",
				          "dayId": "00000000-0000-0000-0000-000000000101",
				          "timeBlock": "MORNING",
				          "title": "Museum visit",
				          "description": "Start with the city museum",
				          "durationMinutes": 90,
				          "isIndoor": true,
				          "tags": ["CULTURAL", "INDOOR"]
				        }
				      ]
				    }
				  ]
				}
				""".trimIndent(),
			)

			val client = HttpGenAiClient(WebClient.builder(), server.baseUrl)
			val schedule = client.generateSchedule(
				GenerationPreferences("Vienna", LocalDate.parse("2026-07-10"), LocalDate.parse("2026-07-11"), "Culture"),
			)

			assertEquals(1, schedule.days.single().dayNumber)
			assertEquals("Museum visit", schedule.days.single().activities.single().title)
			assertEquals(listOf(ActivityTag.CULTURAL, ActivityTag.INDOOR), schedule.days.single().activities.single().tags)

			val request = server.singleRequest()
			assertEquals("POST", request.method)
			assertEquals("/schedules", request.path)
			assertEquals("Vienna", JsonPath.read(request.body, "$.destination"))
			assertEquals("2026-07-10", JsonPath.read(request.body, "$.startDate"))
			assertEquals("Culture", JsonPath.read(request.body, "$.vibe"))
		}
	}

	@Test
	fun `genai client posts alternative activity context and maps response`() {
		RecordingHttpServer().use { server ->
			server.enqueueJson(activityJson("AI indoor climbing session", isIndoor = true))

			val client = HttpGenAiClient(WebClient.builder(), server.baseUrl)
			val originalActivity = activity("Old outdoor plan", isIndoor = false)
			val trip = trip(schedule = Schedule(listOf(day(listOf(originalActivity)))))

			val alternative = client.suggestAlternative(
				RegenerationInstruction("Make this indoor"),
				originalActivity,
				trip,
			)

			assertEquals("AI indoor climbing session", alternative.title)
			assertEquals(true, alternative.isIndoor)

			val request = server.singleRequest()
			assertEquals("POST", request.method)
			assertEquals("/activities/alternative", request.path)
			assertEquals("Make this indoor", JsonPath.read(request.body, "$.instruction"))
			assertEquals("Old outdoor plan", JsonPath.read(request.body, "$.activity.title"))
			assertEquals("Vienna", JsonPath.read(request.body, "$.tripContext.destination"))
			assertEquals("2026-07-10", JsonPath.read(request.body, "$.tripContext.startDate"))
			assertEquals("Old outdoor plan", JsonPath.read(request.body, "$.tripContext.days[0].activities[0].title"))
		}
	}

	@Test
	fun `persistence client sends expected requests and maps traveler auth and trip responses`() {
		RecordingHttpServer().use { server ->
			enqueuePersistenceResponses(server)

			val ids = PersistenceIds()
			val result = exercisePersistenceClient(server, ids)

			assertPersistenceResponses(ids, result)
			assertPersistenceRequests(ids, server.requests())
		}
	}

	private fun enqueuePersistenceResponses(server: RecordingHttpServer) {
		server.enqueueJson(
			"""
			{
			  "id": "00000000-0000-0000-0000-000000000301",
			  "email": "ada@example.com",
			  "isDemo": false,
			  "createdAt": "2026-07-01T10:15:30Z"
			}
			""".trimIndent(),
		)
		server.enqueueJson(
			"""
			{
			  "id": "00000000-0000-0000-0000-000000000301",
			  "email": "ada@example.com",
			  "passwordHash": "hash",
			  "isDemo": false,
			  "createdAt": "2026-07-01T10:15:30Z"
			}
			""".trimIndent(),
		)
		server.enqueueJson(
			"""
			[
			  {
			    "id": "00000000-0000-0000-0000-000000000401",
			    "destination": "Vienna",
			    "startDate": "2026-07-10",
			    "endDate": "2026-07-11"
			  }
			]
			""".trimIndent(),
		)
		server.enqueueJson(tripJson())
		server.enqueueJson(tripJson())
		server.enqueueNoContent()
		server.enqueueJson(activityJson("Updated activity", isIndoor = true))
		server.enqueueNoContent()
	}

	private fun exercisePersistenceClient(
		server: RecordingHttpServer,
		ids: PersistenceIds,
	): PersistenceResult {
		val client = HttpPersistenceClient(WebClient.builder(), server.baseUrl)

		val traveler = client.createTraveler(TravelerCreateRequest("ada@example.com", "hash", isDemo = false))
		val authRecord = client.findTravelerAuthRecordByEmail("ada@example.com")
		val summaries = client.listTrips(ids.travelerId)
		val savedTrip = client.saveTrip(ids.travelerId, trip())
		val fetchedTrip = client.getTrip(ids.travelerId, ids.tripId)
		client.deleteTrip(ids.travelerId, ids.tripId)
		val updatedActivity = client.updateActivity(
			ids.tripId,
			ids.dayId,
			ids.activityId,
			activity("Updated activity", isIndoor = true),
		)
		client.deleteActivity(ids.tripId, ids.dayId, ids.activityId)

		return PersistenceResult(
			travelerId = traveler.id,
			passwordHash = authRecord.passwordHash,
			summaryDestination = summaries.single().destination,
			savedTrip = savedTrip,
			fetchedTrip = fetchedTrip,
			updatedActivity = updatedActivity,
		)
	}

	private fun assertPersistenceResponses(ids: PersistenceIds, result: PersistenceResult) {
		assertEquals(ids.travelerId, result.travelerId)
		assertEquals("hash", result.passwordHash)
		assertEquals("Vienna", result.summaryDestination)
		assertEquals("Vienna", result.savedTrip.destination)
		assertEquals("Vienna", result.fetchedTrip.destination)
		assertEquals("Updated activity", result.updatedActivity.title)
	}

	private fun assertPersistenceRequests(ids: PersistenceIds, requests: List<RecordedRequest>) {
		assertTravelerRequests(requests)
		assertTripRequests(ids, requests)
		assertActivityRequests(ids, requests)
	}

	private fun assertTravelerRequests(requests: List<RecordedRequest>) {
		assertEquals("POST", requests[0].method)
		assertEquals("/travelers", requests[0].path)
		assertEquals("ada@example.com", JsonPath.read(requests[0].body, "$.email"))
		assertFalse(JsonPath.read<Boolean>(requests[0].body, "$.isDemo"))

		assertEquals("GET", requests[1].method)
		assertEquals("/travelers/auth-record", requests[1].path)
		assertEquals("email=ada@example.com", requests[1].query)
	}

	private fun assertTripRequests(ids: PersistenceIds, requests: List<RecordedRequest>) {
		assertEquals("GET", requests[2].method)
		assertEquals("/trips", requests[2].path)
		assertEquals("travelerId=${ids.travelerId}", requests[2].query)

		assertEquals("POST", requests[3].method)
		assertEquals("/trips", requests[3].path)
		assertEquals("travelerId=${ids.travelerId}", requests[3].query)
		assertEquals("Vienna", JsonPath.read(requests[3].body, "$.destination"))

		assertEquals("GET", requests[4].method)
		assertEquals("/trips/${ids.tripId}", requests[4].path)
		assertEquals("travelerId=${ids.travelerId}", requests[4].query)

		assertEquals("DELETE", requests[5].method)
		assertEquals("/trips/${ids.tripId}", requests[5].path)
		assertEquals("travelerId=${ids.travelerId}", requests[5].query)
	}

	private fun assertActivityRequests(ids: PersistenceIds, requests: List<RecordedRequest>) {
		val activityPath = "/trips/${ids.tripId}/days/${ids.dayId}/activities/${ids.activityId}"

		assertEquals("PUT", requests[6].method)
		assertEquals(activityPath, requests[6].path)
		assertTrue(JsonPath.read<Boolean>(requests[6].body, "$.isIndoor"))

		assertEquals("DELETE", requests[7].method)
		assertEquals(activityPath, requests[7].path)
	}

	private data class PersistenceIds(
		val travelerId: UUID = UUID.fromString("00000000-0000-0000-0000-000000000301"),
		val tripId: UUID = UUID.fromString("00000000-0000-0000-0000-000000000401"),
		val dayId: UUID = UUID.fromString("00000000-0000-0000-0000-000000000101"),
		val activityId: UUID = UUID.fromString("00000000-0000-0000-0000-000000000201"),
	)

	private data class PersistenceResult(
		val travelerId: UUID,
		val passwordHash: String,
		val summaryDestination: String,
		val savedTrip: Trip,
		val fetchedTrip: Trip,
		val updatedActivity: Activity,
	)

	private fun trip(schedule: Schedule = Schedule(listOf(day(listOf(activity("Museum visit", isIndoor = true)))))): Trip =
		Trip(
			id = UUID.fromString("00000000-0000-0000-0000-000000000401"),
			destination = "Vienna",
			startDate = LocalDate.parse("2026-07-10"),
			endDate = LocalDate.parse("2026-07-11"),
			vibe = "Culture",
			schedule = schedule,
		)

	private fun day(activities: List<Activity>): Day =
		Day(
			id = UUID.fromString("00000000-0000-0000-0000-000000000101"),
			dayNumber = 1,
			date = LocalDate.parse("2026-07-10"),
			activities = activities,
		)

	private fun activity(title: String, isIndoor: Boolean): Activity =
		Activity(
			id = UUID.fromString("00000000-0000-0000-0000-000000000201"),
			dayId = UUID.fromString("00000000-0000-0000-0000-000000000101"),
			timeBlock = TimeBlock.MORNING,
			title = title,
			description = "A planned activity",
			durationMinutes = 90,
			isIndoor = isIndoor,
			tags = listOf(ActivityTag.CULTURAL),
		)

	private fun tripJson(): String =
		"""
		{
		  "id": "00000000-0000-0000-0000-000000000401",
		  "destination": "Vienna",
		  "startDate": "2026-07-10",
		  "endDate": "2026-07-11",
		  "vibe": "Culture",
		  "schedule": {
		    "days": [
		      {
		        "id": "00000000-0000-0000-0000-000000000101",
		        "dayNumber": 1,
		        "date": "2026-07-10",
		        "activities": [
		          ${activityJson("Museum visit", isIndoor = true)}
		        ]
		      }
		    ]
		  }
		}
		""".trimIndent()

	private fun activityJson(title: String, isIndoor: Boolean): String =
		"""
		{
		  "id": "00000000-0000-0000-0000-000000000201",
		  "dayId": "00000000-0000-0000-0000-000000000101",
		  "timeBlock": "MORNING",
		  "title": "$title",
		  "description": "A planned activity",
		  "durationMinutes": 90,
		  "isIndoor": $isIndoor,
		  "tags": ["CULTURAL"]
		}
		""".trimIndent()
}

private class RecordingHttpServer : AutoCloseable {
	private val responses = ArrayDeque<StubResponse>()
	private val recordedRequests = mutableListOf<RecordedRequest>()
	private val server: HttpServer = HttpServer.create(InetSocketAddress(0), 0)

	val baseUrl: String
		get() = "http://localhost:${server.address.port}"

	init {
		server.createContext("/") { exchange -> handle(exchange) }
		server.start()
	}

	fun enqueueJson(body: String) {
		responses.addLast(StubResponse(200, body, "application/json"))
	}

	fun enqueueNoContent() {
		responses.addLast(StubResponse(204, "", "text/plain"))
	}

	fun singleRequest(): RecordedRequest = requests().single()

	fun requests(): List<RecordedRequest> = recordedRequests.toList()

	override fun close() {
		server.stop(0)
	}

	private fun handle(exchange: HttpExchange) {
		val body = exchange.requestBody.bufferedReader().use { it.readText() }
		recordedRequests.add(
			RecordedRequest(
				method = exchange.requestMethod,
				path = exchange.requestURI.path,
				query = exchange.requestURI.rawQuery,
				body = body,
			),
		)

		val response = responses.removeFirstOrNull()
			?: StubResponse(500, """{"error":"no response queued"}""", "application/json")
		exchange.responseHeaders.add("Content-Type", response.contentType)
		val bytes = response.body.toByteArray(Charsets.UTF_8)
		if (response.status == 204) {
			exchange.sendResponseHeaders(response.status, -1)
		} else {
			exchange.sendResponseHeaders(response.status, bytes.size.toLong())
			exchange.responseBody.use { it.write(bytes) }
		}
		exchange.close()
	}
}

private data class StubResponse(val status: Int, val body: String, val contentType: String)

private data class RecordedRequest(
	val method: String,
	val path: String,
	val query: String?,
	val body: String,
)
