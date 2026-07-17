package com.vacation.app.controller

import org.springframework.core.io.ClassPathResource
import org.springframework.http.MediaType
import org.springframework.http.ResponseEntity
import org.springframework.util.StreamUtils
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.RestController
import java.nio.charset.StandardCharsets

@RestController
class OpenApiController {
	/** Spec file name -> display name in the Swagger UI selector, in listed order. */
	private val specs = linkedMapOf(
		"openapi.yaml" to "App API (public)",
		"gen-ai.yaml" to "GenAI API (internal)",
		"travel-context.yaml" to "Travel Context API (internal)",
	)

	private val specBodies: Map<String, String> by lazy {
		specs.keys.associateWith { name ->
			ClassPathResource(name).inputStream.use { input ->
				StreamUtils.copyToString(input, StandardCharsets.UTF_8)
			}
		}
	}

	@GetMapping("/", produces = [MediaType.TEXT_HTML_VALUE])
	fun documentation(): ResponseEntity<String> =
		ResponseEntity.ok()
			.contentType(MediaType.TEXT_HTML)
			.body(swaggerUiHtml("TripTailor API"))

	@GetMapping(
		"/{spec:openapi|gen-ai|travel-context}.yaml",
		produces = ["application/yaml", "text/yaml", MediaType.TEXT_PLAIN_VALUE],
	)
	fun openApi(@PathVariable spec: String): ResponseEntity<String> {
		val body = specBodies["$spec.yaml"] ?: return ResponseEntity.notFound().build()
		return ResponseEntity.ok()
			.contentType(MediaType.parseMediaType("application/yaml;charset=UTF-8"))
			.body(body)
	}

	private fun swaggerUiHtml(title: String): String {
		// Two leading tabs match the raw string's own indentation, which
		// trimIndent() strips from the interpolated lines too.
		val urlEntries = specs.entries.joinToString(",\n		          ") { (file, label) ->
			"""{ url: basePath + "/$file", name: "$label" }"""
		}
		val primaryName = specs.values.first()
		return """
		<!doctype html>
		<html lang="en">
		<head>
		  <meta charset="utf-8">
		  <meta name="viewport" content="width=device-width, initial-scale=1">
		  <title>$title</title>
		  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css">
		  <style>
		    body { margin: 0; background: #fafafa; }
		    /* The topbar hosts the spec selector, so it has to stay visible.
		       Hide only the Swagger logo and the "explore" URL box, which would
		       let readers point the UI at arbitrary specs. */
		    .swagger-ui .topbar .topbar-wrapper a.link { display: none; }
		    .swagger-ui .topbar .download-url-input { display: none; }
		    .swagger-ui .topbar .download-url-button { display: none; }
		  </style>
		</head>
		<body>
		  <div id="swagger-ui"></div>
		  <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
		  <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-standalone-preset.js"></script>
		  <script>
		    let ui;

		    // The UI is served both at the backend root (:8080/) and behind the
		    // gateway at /api/. The spec declares `servers: /`, so both the spec
		    // fetch and every try-it-out call must be re-based onto whatever
		    // prefix we are actually mounted under.
		    const basePath = window.location.pathname.replace(/\/+${'$'}/, "");

		    function withBasePath(url) {
		      if (!basePath) {
		        return url;
		      }
		      const resolved = new URL(url, window.location.origin);
		      if (resolved.origin === window.location.origin && !resolved.pathname.startsWith(basePath + "/")) {
		        resolved.pathname = basePath + resolved.pathname;
		      }
		      return resolved.toString();
		    }

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
		      request.url = withBasePath(request.url);
		      const token = localStorage.getItem("triptailorAccessToken");
		      if (token && !request.url.includes("/auth/")) {
		        request.headers = request.headers || {};
		        request.headers.Authorization = "Bearer " + token;
		      }
		      return request;
		    }

		    window.onload = () => {
		      ui = SwaggerUIBundle({
		        urls: [
		          $urlEntries
		        ],
		        "urls.primaryName": "$primaryName",
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
}
