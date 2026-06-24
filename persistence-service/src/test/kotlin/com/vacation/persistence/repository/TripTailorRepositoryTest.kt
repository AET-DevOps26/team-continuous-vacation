package com.vacation.persistence.repository

import com.vacation.persistence.api.ApiException
import com.vacation.persistence.api.TravelerCreateRequest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.mockito.Mockito.mock
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate

class TripTailorRepositoryTest {
	private val repository = TripTailorRepository(mock(NamedParameterJdbcTemplate::class.java))

	@Test
	fun `registered traveler requires email and password hash`() {
		val exception = assertThrows(ApiException::class.java) {
			repository.createTraveler(TravelerCreateRequest(isDemo = false))
		}

		assertEquals(400, exception.status)
		assertEquals("INVALID_TRAVELER", exception.type)
	}

	@Test
	fun `registered traveler rejects blank email`() {
		val exception = assertThrows(ApiException::class.java) {
			repository.createTraveler(TravelerCreateRequest(email = " ", passwordHash = "hash", isDemo = false))
		}

		assertEquals(400, exception.status)
		assertEquals("INVALID_TRAVELER", exception.type)
	}

	@Test
	fun `demo traveler can omit email and password hash`() {
		val traveler = repository.createTraveler(TravelerCreateRequest(isDemo = true))

		assertTrue(traveler.isDemo)
		assertNull(traveler.email)
	}
}
