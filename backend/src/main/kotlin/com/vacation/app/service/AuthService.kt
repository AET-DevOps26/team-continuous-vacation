package com.vacation.app.service

import com.vacation.app.api.ApiException
import com.vacation.app.api.AuthResponse
import com.vacation.app.api.LoginRequest
import com.vacation.app.api.RegisterRequest
import com.vacation.app.api.TravelerCreateRequest
import com.vacation.app.client.PersistenceClient
import org.springframework.security.crypto.password.PasswordEncoder
import org.springframework.stereotype.Service
import org.springframework.web.reactive.function.client.WebClientResponseException

@Service
class AuthService(
	private val persistenceClient: PersistenceClient,
	private val passwordEncoder: PasswordEncoder,
	private val tokenService: TokenService,
) {
	fun register(request: RegisterRequest): AuthResponse {
		try {
			val traveler = persistenceClient.createTraveler(
				TravelerCreateRequest(
					email = request.email.lowercase(),
					passwordHash = passwordEncoder.encode(request.password),
					isDemo = false,
				),
			)
			return tokenService.issueTravelerToken(traveler.id, traveler.isDemo)
		} catch (exception: WebClientResponseException.Conflict) {
			throw ApiException(409, "EMAIL_ALREADY_REGISTERED", "E-mail Already Registered")
		}
	}

	fun login(request: LoginRequest): AuthResponse {
		val traveler = try {
			persistenceClient.findTravelerAuthRecordByEmail(request.email.lowercase())
		} catch (exception: WebClientResponseException.NotFound) {
			throw ApiException(401, "INVALID_CREDENTIALS", "Invalid Credentials")
		}

		if (!passwordEncoder.matches(request.password, traveler.passwordHash)) {
			throw ApiException(401, "INVALID_CREDENTIALS", "Invalid Credentials")
		}
		return tokenService.issueTravelerToken(traveler.id, traveler.isDemo)
	}

	fun createDemoSession(): AuthResponse {
		val traveler = persistenceClient.createTraveler(TravelerCreateRequest(isDemo = true))
		return tokenService.issueTravelerToken(traveler.id, traveler.isDemo)
	}
}
