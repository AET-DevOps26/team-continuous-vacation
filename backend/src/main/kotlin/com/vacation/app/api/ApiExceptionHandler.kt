package com.vacation.app.api

import org.springframework.http.ResponseEntity
import org.springframework.web.bind.MethodArgumentNotValidException
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice
import org.springframework.web.reactive.function.client.WebClientResponseException

@RestControllerAdvice
class ApiExceptionHandler {
	@ExceptionHandler(ApiException::class)
	fun handleApiException(exception: ApiException): ResponseEntity<ApiError> =
		ResponseEntity
			.status(exception.status)
			.body(ApiError(exception.type, exception.message, exception.detail, exception.status))

	@ExceptionHandler(MethodArgumentNotValidException::class)
	fun handleValidation(exception: MethodArgumentNotValidException): ResponseEntity<ApiError> =
		ResponseEntity
			.badRequest()
			.body(ApiError("VALIDATION_FAILED", "Validation Failed", exception.message, 400))

	@ExceptionHandler(WebClientResponseException::class)
	fun handleWebClient(exception: WebClientResponseException): ResponseEntity<ApiError> {
		val status = exception.statusCode.value()
		return ResponseEntity
			.status(status)
			.body(ApiError("UPSTREAM_ERROR", "Upstream Error", exception.responseBodyAsString, status))
	}
}
