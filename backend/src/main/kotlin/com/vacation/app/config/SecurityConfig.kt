package com.vacation.app.config

import com.nimbusds.jose.jwk.source.ImmutableSecret
import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.http.HttpStatus
import org.springframework.http.MediaType
import org.springframework.security.config.Customizer
import org.springframework.security.config.annotation.web.builders.HttpSecurity
import org.springframework.security.config.http.SessionCreationPolicy
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder
import org.springframework.security.crypto.password.PasswordEncoder
import org.springframework.security.oauth2.jose.jws.MacAlgorithm
import org.springframework.security.oauth2.jwt.JwtDecoder
import org.springframework.security.oauth2.jwt.JwtEncoder
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder
import org.springframework.security.web.SecurityFilterChain
import javax.crypto.spec.SecretKeySpec

@Configuration
class SecurityConfig {
	@Bean
	fun securityFilterChain(http: HttpSecurity): SecurityFilterChain =
		http
			.csrf { it.disable() }
			.sessionManagement { it.sessionCreationPolicy(SessionCreationPolicy.STATELESS) }
			.authorizeHttpRequests {
				it.requestMatchers("/", "/openapi.yaml", "/health", "/actuator/health", "/auth/**").permitAll()
				it.anyRequest().authenticated()
			}
			.exceptionHandling {
				it.authenticationEntryPoint { _, response, _ ->
					response.status = HttpStatus.UNAUTHORIZED.value()
					response.contentType = MediaType.APPLICATION_JSON_VALUE
					response.writer.write("""{"type":"UNAUTHORIZED","title":"Unauthorized","detail":"A valid bearer token is required.","status":401}""")
				}
			}
			.oauth2ResourceServer { it.jwt(Customizer.withDefaults()) }
			.build()

	@Bean
	fun passwordEncoder(): PasswordEncoder = BCryptPasswordEncoder()

	@Bean
	fun jwtSecretKey(@Value("\${security.jwt.secret}") secret: String): SecretKeySpec {
		require(secret.toByteArray().size >= 32) { "security.jwt.secret must be at least 32 bytes for HS256." }
		return SecretKeySpec(secret.toByteArray(), "HmacSHA256")
	}

	@Bean
	fun jwtEncoder(secretKey: SecretKeySpec): JwtEncoder = NimbusJwtEncoder(ImmutableSecret(secretKey))

	@Bean
	fun jwtDecoder(secretKey: SecretKeySpec): JwtDecoder =
		NimbusJwtDecoder.withSecretKey(secretKey)
			.macAlgorithm(MacAlgorithm.HS256)
			.build()
}
