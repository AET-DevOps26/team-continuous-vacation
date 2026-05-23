package com.vacation.app.api

import jakarta.validation.constraints.Email
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.Size
import java.time.Instant
import java.time.LocalDate
import java.util.UUID

data class RegisterRequest(
	@field:Email val email: String,
	@field:Size(min = 8) val password: String,
)

data class LoginRequest(
	@field:Email val email: String,
	@field:NotBlank val password: String,
)

data class AuthResponse(
	val travelerId: UUID,
	val isDemo: Boolean,
	val accessToken: String,
	val tokenType: String = "Bearer",
	val expiresAt: Instant,
)

data class GenerationPreferences(
	@field:NotBlank val destination: String,
	val startDate: LocalDate,
	val endDate: LocalDate,
	@field:NotBlank val vibe: String,
)

data class RegenerationInstruction(@field:NotBlank val instruction: String)

data class TripSummary(
	val id: UUID,
	val destination: String,
	val startDate: LocalDate,
	val endDate: LocalDate,
)

data class Trip(
	val id: UUID,
	val destination: String,
	val startDate: LocalDate,
	val endDate: LocalDate,
	val vibe: String,
	val schedule: Schedule,
)

data class Schedule(val days: List<Day>)

data class Day(
	val id: UUID,
	val dayNumber: Int,
	val date: LocalDate,
	val activities: List<Activity>,
)

data class Activity(
	val id: UUID,
	val dayId: UUID,
	val timeBlock: TimeBlock,
	val title: String,
	val description: String,
	val durationMinutes: Int,
	val isIndoor: Boolean? = null,
	val tags: List<ActivityTag>? = null,
)

enum class TimeBlock { MORNING, NOON, AFTERNOON, EVENING, NIGHT }

enum class ActivityTag {
	OUTDOOR,
	INDOOR,
	CULTURAL,
	SPORTY,
	RELAXING,
	ADVENTUROUS,
	FOOD,
	SHOPPING,
	ENTERTAINMENT,
	FAMILY_FRIENDLY,
	PARTY,
}

data class TravelerCreateRequest(
	val email: String? = null,
	val passwordHash: String? = null,
	val isDemo: Boolean,
)

data class Traveler(
	val id: UUID,
	val email: String? = null,
	val isDemo: Boolean,
	val createdAt: Instant,
)

data class TravelerAuthRecord(
	val id: UUID,
	val email: String,
	val passwordHash: String,
	val isDemo: Boolean,
	val createdAt: Instant,
)

data class ApiError(
	val type: String,
	val title: String,
	val detail: String? = null,
	val status: Int,
)
