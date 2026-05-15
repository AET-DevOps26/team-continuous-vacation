package com.vacation.app.controller

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
			.body(swaggerUiHtml("TripTailor App API"))

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
		    let ui;

		    function rememberTokenFrom(response) {
		      try {
		        const body = JSON.parse(response.text || "{}");
		        if (body.accessToken) {
		          localStorage.setItem("triptailorAccessToken", body.accessToken);
		          if (ui) {
		            ui.preauthorizeApiKey("bearerAuth", body.accessToken);
		          }
		        }
		      } catch (ignored) {
		      }
		      return response;
		    }

		    function attachStoredToken(request) {
		      const token = localStorage.getItem("triptailorAccessToken");
		      if (token && !request.url.includes("/auth/")) {
		        request.headers = request.headers || {};
		        request.headers.Authorization = "Bearer " + token;
		      }
		      return request;
		    }

		    window.onload = () => {
		      ui = SwaggerUIBundle({
		        url: "/openapi.yaml",
		        dom_id: "#swagger-ui",
		        deepLinking: true,
		        requestInterceptor: attachStoredToken,
		        responseInterceptor: rememberTokenFrom,
		        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
		        layout: "StandaloneLayout"
		      });
		      window.ui = ui;

		      const token = localStorage.getItem("triptailorAccessToken");
		      if (token) {
		        ui.preauthorizeApiKey("bearerAuth", token);
		      }
		    };
		  </script>
		</body>
		</html>
		""".trimIndent()
}
