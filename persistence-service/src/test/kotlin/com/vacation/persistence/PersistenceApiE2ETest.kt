package com.vacation.persistence

import com.jayway.jsonpath.JsonPath
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
import org.springframework.http.MediaType
import org.springframework.test.context.TestPropertySource
import org.springframework.test.context.junit.jupiter.SpringExtension
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.delete
import org.springframework.test.web.servlet.get
import org.springframework.test.web.servlet.post
import org.springframework.test.web.servlet.put
import java.util.UUID
import org.junit.jupiter.api.extension.ExtendWith

@ExtendWith(SpringExtension::class)
@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(
	properties = [
		"spring.datasource.url=jdbc:h2:mem:persistence;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
		"spring.datasource.driver-class-name=org.h2.Driver",
		"spring.datasource.username=sa",
		"spring.datasource.password=",
	],
)
class PersistenceApiE2ETest {
	@Autowired
	private lateinit var mockMvc: MockMvc

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
				content { string(org.hamcrest.Matchers.containsString("TripTailor Persistence API")) }
			}

		mockMvc.get("/openapi.yaml")
			.andExpect {
				status { isOk() }
				content { string(org.hamcrest.Matchers.containsString("title: TripTailor — Persistence API")) }
				content { string(org.hamcrest.Matchers.containsString("Internal database access layer")) }
				content { string(org.hamcrest.Matchers.containsString("/health:")) }
				content { string(org.hamcrest.Matchers.containsString("/travelers/auth-record:")) }
			}
	}

	@Test
	fun `traveler and trip lifecycle persists relational data`() {
		val email = "ada-${UUID.randomUUID()}@example.com"
		val createdTravelerJson = mockMvc.post("/travelers") {
			contentType = MediaType.APPLICATION_JSON
			content = """{"email":"$email","passwordHash":"hash","isDemo":false}"""
		}.andExpect {
			status { isCreated() }
			jsonPath("$.passwordHash") { doesNotExist() }
		}.andReturn().response.contentAsString
		val travelerId = JsonPath.read<String>(createdTravelerJson, "$.id")

		mockMvc.get("/travelers?email=$email")
			.andExpect {
				status { isOk() }
				jsonPath("$.passwordHash") { doesNotExist() }
			}

		mockMvc.get("/travelers/auth-record?email=$email")
			.andExpect {
				status { isOk() }
				jsonPath("$.passwordHash") { value("hash") }
			}

		val tripId = UUID.randomUUID()
		val dayId = UUID.randomUUID()
		val activityId = UUID.randomUUID()

		mockMvc.post("/trips?travelerId=$travelerId") {
			contentType = MediaType.APPLICATION_JSON
			content = """
				{
				  "id":"$tripId",
				  "destination":"Munich",
				  "startDate":"2026-05-15",
				  "endDate":"2026-05-15",
				  "vibe":"Sporty",
				  "schedule":{"days":[{"id":"$dayId","dayNumber":1,"date":"2026-05-15","activities":[{"id":"$activityId","dayId":"$dayId","timeBlock":"MORNING","title":"Run","description":"Park run","durationMinutes":60,"isIndoor":false,"tags":["SPORTY"]}]}]}
				}
			""".trimIndent()
		}.andExpect {
			status { isCreated() }
			jsonPath("$.schedule.days[0].activities[0].title") { value("Run") }
		}

		mockMvc.get("/trips/$tripId?travelerId=$travelerId")
			.andExpect {
				status { isOk() }
				jsonPath("$.destination") { value("Munich") }
			}

		val replacementId = UUID.randomUUID()
		mockMvc.put("/trips/$tripId/days/$dayId/activities/$activityId") {
			contentType = MediaType.APPLICATION_JSON
			content = """{"id":"$replacementId","dayId":"$dayId","timeBlock":"AFTERNOON","title":"Museum","description":"Indoor visit","durationMinutes":90,"isIndoor":true,"tags":["INDOOR"]}"""
		}.andExpect {
			status { isOk() }
			jsonPath("$.title") { value("Museum") }
		}

		mockMvc.delete("/trips/$tripId?travelerId=$travelerId")
			.andExpect { status { isNoContent() } }
	}
}
