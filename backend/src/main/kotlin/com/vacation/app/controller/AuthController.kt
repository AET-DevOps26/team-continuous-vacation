package com.vacation.app.controller

import com.vacation.app.api.AuthResponse
import com.vacation.app.api.LoginRequest
import com.vacation.app.api.RegisterRequest
import com.vacation.app.service.AuthService
import jakarta.validation.Valid
import org.springframework.http.HttpStatus
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.ResponseStatus
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/auth")
class AuthController(private val authService: AuthService) {
	@PostMapping("/register")
	@ResponseStatus(HttpStatus.CREATED)
	fun register(@Valid @RequestBody request: RegisterRequest): AuthResponse = authService.register(request)

	@PostMapping("/login")
	fun login(@Valid @RequestBody request: LoginRequest): AuthResponse = authService.login(request)

	@PostMapping("/demo")
	@ResponseStatus(HttpStatus.CREATED)
	fun createDemoSession(): AuthResponse = authService.createDemoSession()
}
