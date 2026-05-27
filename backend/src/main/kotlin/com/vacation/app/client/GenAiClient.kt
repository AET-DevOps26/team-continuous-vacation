package com.vacation.app.client

import com.vacation.app.api.Activity
import com.vacation.app.api.GenerationPreferences
import com.vacation.app.api.RegenerationInstruction
import com.vacation.app.api.Schedule
import com.vacation.app.api.Trip

interface GenAiClient {
	fun generateSchedule(preferences: GenerationPreferences): Schedule

	fun suggestAlternative(instruction: RegenerationInstruction, activity: Activity, tripContext: Trip): Activity
}
