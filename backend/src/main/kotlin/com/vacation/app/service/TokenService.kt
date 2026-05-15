package com.vacation.app.service

import com.vacation.app.api.AuthResponse
import org.springframework.beans.factory.annotation.Value
import org.springframework.security.oauth2.jose.jws.MacAlgorithm
import org.springframework.security.oauth2.jwt.JwsHeader
import org.springframework.security.oauth2.jwt.JwtClaimsSet
import org.springframework.security.oauth2.jwt.JwtEncoder
import org.springframework.security.oauth2.jwt.JwtEncoderParameters
import org.springframework.stereotype.Service
import java.time.Clock
import java.time.Instant
import java.time.temporal.ChronoUnit
import java.util.UUID

@Service
class TokenService(
	private val jwtEncoder: JwtEncoder,
	@Value("\${security.jwt.issuer}") private val issuer: String,
	@Value("\${security.jwt.ttl-days}") private val ttlDays: Long,
) {
	private val clock: Clock = Clock.systemUTC()

	fun issueTravelerToken(travelerId: UUID, isDemo: Boolean): AuthResponse {
		val issuedAt = Instant.now(clock)
		val expiresAt = issuedAt.plus(ttlDays, ChronoUnit.DAYS)
		val claims = JwtClaimsSet.builder()
			.issuer(issuer)
			.issuedAt(issuedAt)
			.expiresAt(expiresAt)
			.subject(travelerId.toString())
			.claim("traveler_id", travelerId.toString())
			.claim("is_demo", isDemo)
			.build()
		val headers = JwsHeader.with(MacAlgorithm.HS256).build()
		val token = jwtEncoder.encode(JwtEncoderParameters.from(headers, claims)).tokenValue
		return AuthResponse(travelerId, isDemo, token, expiresAt = expiresAt)
	}
}
