package com.vacation.app

import com.sun.net.httpserver.HttpServer
import io.micrometer.observation.Observation
import io.micrometer.observation.ObservationRegistry
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.web.reactive.function.client.WebClient
import java.net.InetSocketAddress
import java.util.concurrent.atomic.AtomicReference

@SpringBootTest(
	properties = [
		"management.tracing.sampling.probability=1.0",
		"management.opentelemetry.tracing.export.otlp.endpoint=http://localhost:4318/v1/traces",
	],
)
class WebClientTracingTests {
	@Autowired
	private lateinit var webClientBuilder: WebClient.Builder

	@Autowired
	private lateinit var observationRegistry: ObservationRegistry

	@Test
	fun `webclient propagates traceparent header from current observation`() {
		val traceparent = AtomicReference<String?>()
		val server = HttpServer.create(InetSocketAddress(0), 0)
		server.createContext("/probe") { exchange ->
			traceparent.set(exchange.requestHeaders.getFirst("traceparent"))
			exchange.sendResponseHeaders(204, -1)
			exchange.close()
		}
		server.start()

		try {
			Observation.createNotStarted("test.parent", observationRegistry).observe {
				webClientBuilder
					.baseUrl("http://localhost:${server.address.port}")
					.build()
					.get()
					.uri("/probe")
					.retrieve()
					.toBodilessEntity()
					.block()
			}

			val propagated = traceparent.get()
			assertNotNull(propagated)
			assertTrue(
				propagated!!.matches(Regex("00-[0-9a-f]{32}-[0-9a-f]{16}-0[01]")),
				"traceparent header should use W3C trace context format",
			)
		} finally {
			server.stop(0)
		}
	}
}
