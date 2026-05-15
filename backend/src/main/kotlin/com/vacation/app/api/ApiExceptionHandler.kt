package com.vacation.app.api

import org.springframework.http.HttpStatus
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
		val type = when (status) {
			401 -> "INVALID_CREDENTIALS"
			404 -> "NOT_FOUND"
			409 -> "CONFLICT"
			else -> "UPSTREAM_ERROR"
		}
		return ResponseEntity
			.status(status)
			.body(ApiError(type, HttpStatus.valueOf(status).reasonPhrase, exception.responseBodyAsString, status))
	}
}
