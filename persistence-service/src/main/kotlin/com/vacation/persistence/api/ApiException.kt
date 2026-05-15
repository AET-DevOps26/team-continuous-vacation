package com.vacation.persistence.api

class ApiException(
	val status: Int,
	val type: String,
	override val message: String,
	val detail: String? = null,
) : RuntimeException(message)
