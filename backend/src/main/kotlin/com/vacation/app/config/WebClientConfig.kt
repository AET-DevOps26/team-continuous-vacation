package com.vacation.app.config

import io.micrometer.observation.ObservationRegistry
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.web.reactive.function.client.WebClient

@Configuration
class WebClientConfig {
	@Bean
	fun webClientBuilder(observationRegistry: ObservationRegistry): WebClient.Builder =
		WebClient.builder().observationRegistry(observationRegistry)
}
