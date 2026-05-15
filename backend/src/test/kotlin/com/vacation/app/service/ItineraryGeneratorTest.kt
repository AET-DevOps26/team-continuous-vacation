package com.vacation.app.service

import com.vacation.app.api.GenerationPreferences
import com.vacation.app.api.RegenerationInstruction
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.time.LocalDate

class ItineraryGeneratorTest {
	private val generator = ItineraryGenerator()

	@Test
	fun `generate creates one scheduled day per inclusive trip date`() {
		val trip = generator.generate(
			GenerationPreferences(
				destination = "Munich",
				startDate = LocalDate.parse("2026-05-15"),
				endDate = LocalDate.parse("2026-05-17"),
				vibe = "Sporty",
			),
		)

		assertEquals(3, trip.schedule.days.size)
		assertTrue(trip.schedule.days.all { it.activities.size == 3 })
	}

	@Test
	fun `regenerate keeps parent day and marks indoor instructions`() {
		val activity = generator.generate(
			GenerationPreferences("Munich", LocalDate.parse("2026-05-15"), LocalDate.parse("2026-05-15"), "Food"),
		).schedule.days.first().activities.first()

		val replacement = generator.regenerate(activity, RegenerationInstruction("Make this indoor"))

		assertEquals(activity.dayId, replacement.dayId)
		assertEquals(true, replacement.isIndoor)
		assertTrue(replacement.title.startsWith("Updated:"))
	}
}
