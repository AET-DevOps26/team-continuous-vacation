package com.vacation.persistence.api

import org.springframework.dao.DuplicateKeyException
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.MethodArgumentNotValidException
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice

@RestControllerAdvice
class ApiExceptionHandler {
	@ExceptionHandler(ApiException::class)
	fun handleApiException(exception: ApiException): ResponseEntity<ApiError> =
		ResponseEntity.status(exception.status).body(ApiError(exception.type, exception.message, exception.detail, exception.status))

	@ExceptionHandler(DuplicateKeyException::class)
	fun handleDuplicateKey(): ResponseEntity<ApiError> =
		ResponseEntity.status(409).body(ApiError("EMAIL_ALREADY_EXISTS", "E-mail Already Exists", null, 409))

	@ExceptionHandler(MethodArgumentNotValidException::class)
	fun handleValidation(exception: MethodArgumentNotValidException): ResponseEntity<ApiError> =
		ResponseEntity.badRequest().body(ApiError("VALIDATION_FAILED", "Validation Failed", exception.message, 400))
}
