package com.vacation.app.client

import com.vacation.app.api.Activity
import com.vacation.app.api.Day
import com.vacation.app.api.GenerationPreferences
import com.vacation.app.api.RegenerationInstruction
import com.vacation.app.api.Schedule
import com.vacation.app.api.Trip
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Component
import org.springframework.web.reactive.function.client.WebClient
import java.time.LocalDate

@Component
class HttpGenAiClient(
	builder: WebClient.Builder,
	@Value("\${services.genai.base-url:http://localhost:8000}") baseUrl: String,
) : GenAiClient {
	private val webClient = builder.baseUrl(baseUrl).build()

	override fun generateSchedule(preferences: GenerationPreferences): Schedule =
		webClient.post()
			.uri("/schedules")
			.bodyValue(preferences)
			.retrieve()
			.bodyToMono(Schedule::class.java)
			.block()!!

	override fun suggestAlternative(instruction: RegenerationInstruction, activity: Activity, tripContext: Trip): Activity =
		webClient.post()
			.uri("/activities/alternative")
			.bodyValue(AlternativeActivityRequest(instruction.instruction, activity, tripContext.toContext()))
			.retrieve()
			.bodyToMono(Activity::class.java)
			.block()!!

	private fun Trip.toContext(): TripContext =
		TripContext(destination, startDate, endDate, vibe, schedule.days)
}

private data class AlternativeActivityRequest(
	val instruction: String,
	val activity: Activity,
	val tripContext: TripContext,
)

private data class TripContext(
	val destination: String,
	val startDate: LocalDate,
	val endDate: LocalDate,
	val vibe: String,
	val days: List<Day>,
)
