package com.vacation.app.controller

import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RestController
import java.net.InetAddress

@RestController
class DebugController {
	@GetMapping("/debug/instance")
	fun instance(): Map<String, String> =
		mapOf(
			"service" to "backend",
			"instance" to (System.getenv("HOSTNAME") ?: InetAddress.getLocalHost().hostName),
		)
}
