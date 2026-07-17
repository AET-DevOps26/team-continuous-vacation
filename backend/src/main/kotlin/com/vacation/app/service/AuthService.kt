package com.vacation.app.service

import com.vacation.app.api.ApiException
import com.vacation.app.api.AuthResponse
import com.vacation.app.api.LoginRequest
import com.vacation.app.api.RegisterRequest
import com.vacation.app.api.TravelerCreateRequest
import com.vacation.app.repository.TripTailorRepository
import org.springframework.dao.DuplicateKeyException
import org.springframework.security.crypto.password.PasswordEncoder
import org.springframework.stereotype.Service

@Service
class AuthService(
	private val repository: TripTailorRepository,
	private val passwordEncoder: PasswordEncoder,
	private val tokenService: TokenService,
) {
	fun register(request: RegisterRequest): AuthResponse {
		try {
			val traveler = repository.createTraveler(
				TravelerCreateRequest(
					email = request.email.lowercase(),
					passwordHash = passwordEncoder.encode(request.password),
					isDemo = false,
				),
			)
			return tokenService.issueTravelerToken(traveler.id, traveler.isDemo)
		} catch (exception: DuplicateKeyException) {
			throw ApiException(409, "EMAIL_ALREADY_REGISTERED", "E-mail Already Registered")
		}
	}

	fun login(request: LoginRequest): AuthResponse {
		val traveler = try {
			repository.findTravelerAuthRecordByEmail(request.email.lowercase())
		} catch (exception: ApiException) {
			throw ApiException(401, "INVALID_CREDENTIALS", "Invalid Credentials")
		}

		if (!passwordEncoder.matches(request.password, traveler.passwordHash)) {
			throw ApiException(401, "INVALID_CREDENTIALS", "Invalid Credentials")
		}
		return tokenService.issueTravelerToken(traveler.id, traveler.isDemo)
	}

	fun createDemoSession(): AuthResponse {
		val traveler = repository.createTraveler(TravelerCreateRequest(isDemo = true))
		return tokenService.issueTravelerToken(traveler.id, traveler.isDemo)
	}
}
