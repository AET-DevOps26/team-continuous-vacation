package com.vacation.persistence.controller

import org.springframework.core.io.ClassPathResource
import org.springframework.http.MediaType
import org.springframework.http.ResponseEntity
import org.springframework.util.StreamUtils
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RestController
import java.nio.charset.StandardCharsets

@RestController
class OpenApiController {
	private val openApiYaml: String by lazy {
		ClassPathResource("openapi.yaml").inputStream.use { input ->
			StreamUtils.copyToString(input, StandardCharsets.UTF_8)
		}
	}

	@GetMapping("/", produces = [MediaType.TEXT_HTML_VALUE])
	fun documentation(): ResponseEntity<String> =
		ResponseEntity.ok()
			.contentType(MediaType.TEXT_HTML)
			.body(swaggerUiHtml("TripTailor Persistence API"))

	@GetMapping("/openapi.yaml", produces = ["application/yaml", "text/yaml", MediaType.TEXT_PLAIN_VALUE])
	fun openApi(): ResponseEntity<String> =
		ResponseEntity.ok()
			.contentType(MediaType.parseMediaType("application/yaml;charset=UTF-8"))
			.body(openApiYaml)

	private fun swaggerUiHtml(title: String): String =
		"""
		<!doctype html>
		<html lang="en">
		<head>
		  <meta charset="utf-8">
		  <meta name="viewport" content="width=device-width, initial-scale=1">
		  <title>$title</title>
		  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css">
		  <style>
		    body { margin: 0; background: #fafafa; }
		    .swagger-ui .topbar { display: none; }
		  </style>
		</head>
		<body>
		  <div id="swagger-ui"></div>
		  <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
		  <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-standalone-preset.js"></script>
		  <script>
		    window.onload = () => {
		      window.ui = SwaggerUIBundle({
		        url: "/openapi.yaml",
		        dom_id: "#swagger-ui",
		        deepLinking: true,
		        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
		        layout: "StandaloneLayout"
		      });
		    };
		  </script>
		</body>
		</html>
		""".trimIndent()
}
