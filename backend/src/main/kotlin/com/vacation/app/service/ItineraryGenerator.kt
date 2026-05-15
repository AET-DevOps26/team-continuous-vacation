package com.vacation.app.service

import com.vacation.app.api.Activity
import com.vacation.app.api.ActivityTag
import com.vacation.app.api.Day
import com.vacation.app.api.GenerationPreferences
import com.vacation.app.api.RegenerationInstruction
import com.vacation.app.api.Schedule
import com.vacation.app.api.TimeBlock
import com.vacation.app.api.Trip
import org.springframework.stereotype.Service
import java.time.temporal.ChronoUnit
import java.util.UUID

@Service
class ItineraryGenerator {
	fun generate(preferences: GenerationPreferences): Trip {
		require(!preferences.endDate.isBefore(preferences.startDate)) { "endDate must be on or after startDate" }
		val dayCount = ChronoUnit.DAYS.between(preferences.startDate, preferences.endDate).toInt() + 1
		val days = (0 until dayCount).map { offset ->
			val dayId = UUID.randomUUID()
			val date = preferences.startDate.plusDays(offset.toLong())
			Day(
				id = dayId,
				dayNumber = offset + 1,
				date = date,
				activities = listOf(
					activity(dayId, TimeBlock.MORNING, "Explore ${preferences.destination}", "Start with a ${preferences.vibe.lowercase()} overview of the city.", false),
					activity(dayId, TimeBlock.AFTERNOON, "Local highlight in ${preferences.destination}", "Visit a well-rated attraction that matches the trip vibe.", false),
					activity(dayId, TimeBlock.EVENING, "Dinner and wind-down", "Choose a local dinner spot and keep the evening flexible.", true),
				),
			)
		}
		return Trip(UUID.randomUUID(), preferences.destination, preferences.startDate, preferences.endDate, preferences.vibe, Schedule(days))
	}

	fun regenerate(current: Activity, instruction: RegenerationInstruction): Activity =
		current.copy(
			id = UUID.randomUUID(),
			title = "Updated: ${current.title}",
			description = "Replacement based on instruction: ${instruction.instruction}",
			isIndoor = instruction.instruction.contains("indoor", ignoreCase = true).takeIf { it } ?: current.isIndoor,
			tags = mergeTags(current.tags, instruction.instruction),
		)

	private fun activity(dayId: UUID, block: TimeBlock, title: String, description: String, indoor: Boolean) =
		Activity(
			id = UUID.randomUUID(),
			dayId = dayId,
			timeBlock = block,
			title = title,
			description = description,
			durationMinutes = if (block == TimeBlock.EVENING) 90 else 120,
			isIndoor = indoor,
			tags = if (indoor) listOf(ActivityTag.INDOOR, ActivityTag.FOOD) else listOf(ActivityTag.OUTDOOR, ActivityTag.CULTURAL),
		)

	private fun mergeTags(existing: List<ActivityTag>?, instruction: String): List<ActivityTag> {
		val tags = existing.orEmpty().toMutableSet()
		if (instruction.contains("indoor", ignoreCase = true)) tags.add(ActivityTag.INDOOR)
		if (instruction.contains("food", ignoreCase = true)) tags.add(ActivityTag.FOOD)
		return tags.toList()
	}
}
