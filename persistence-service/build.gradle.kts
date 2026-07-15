import java.math.BigDecimal

plugins {
	kotlin("jvm") version "2.2.21"
	kotlin("plugin.spring") version "2.2.21"
	id("org.springframework.boot") version "4.0.6"
	id("io.spring.dependency-management") version "1.1.7"
	id("dev.detekt") version "2.0.0-alpha.5"
	jacoco
}

group = "com.vacation"
version = "0.0.1-SNAPSHOT"

java {
	toolchain {
		languageVersion = JavaLanguageVersion.of(21)
	}
}

repositories {
	mavenCentral()
}

configurations.matching { it.name == "detekt" }.configureEach {
	resolutionStrategy.eachDependency {
		if (requested.group == "org.jetbrains.kotlin") {
			useVersion("2.4.0")
		}
	}
}

detekt {
	baseline = file("detekt-baseline.xml")
}

dependencies {
	implementation("org.springframework.boot:spring-boot-starter-actuator")
	implementation("org.springframework.boot:spring-boot-starter-opentelemetry")
	implementation("org.springframework.boot:spring-boot-starter-jdbc")
	implementation("org.springframework.boot:spring-boot-starter-validation")
	implementation("org.springframework.boot:spring-boot-starter-webmvc")
	implementation("org.jetbrains.kotlin:kotlin-reflect")
	implementation("com.fasterxml.jackson.core:jackson-databind")
	implementation("tools.jackson.module:jackson-module-kotlin")
	runtimeOnly("io.micrometer:micrometer-registry-prometheus")
	runtimeOnly("org.postgresql:postgresql")
	testRuntimeOnly("com.h2database:h2")
	testImplementation("org.springframework.boot:spring-boot-starter-test")
	testImplementation("org.springframework.boot:spring-boot-starter-actuator-test")
	testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
	testImplementation("org.jetbrains.kotlin:kotlin-test-junit5")
	testRuntimeOnly("org.junit.platform:junit-platform-launcher")
	developmentOnly("org.springframework.boot:spring-boot-devtools")

}

// Security: force patched transitive versions flagged by the Trivy image scan.
// eachDependency wins over the io.spring.dependency-management BOM (plain Gradle
// constraints do not). Remove once the managed Spring Boot BOM ships these versions.
configurations.all {
	resolutionStrategy.eachDependency {
		when {
			requested.group == "org.apache.tomcat.embed" ->
				useVersion("11.0.22") // CVE-2026-41293/43512/43515 (CRITICAL)
			requested.group == "com.fasterxml.jackson.core" && requested.name == "jackson-databind" ->
				useVersion("2.21.4") // CVE-2026-54512/54513
			requested.group == "tools.jackson.core" && requested.name == "jackson-databind" ->
				useVersion("3.1.4") // CVE-2026-54512/54513
			requested.group == "org.postgresql" && requested.name == "postgresql" ->
				useVersion("42.7.11") // CVE-2026-42198
		}
	}
}

kotlin {
	compilerOptions {
		freeCompilerArgs.addAll("-Xjsr305=strict", "-Xannotation-default-target=param-property")
	}
}

val copyOpenApiSpec by tasks.registering(Copy::class) {
	from("${rootProject.projectDir}/../api-specification/persistance.yaml")
	into(layout.projectDirectory.dir("src/main/resources"))
	rename { "openapi.yaml" }
}

tasks.processResources {
	dependsOn(copyOpenApiSpec)
}

tasks.withType<Test> {
	useJUnitPlatform()
	finalizedBy(tasks.jacocoTestReport)
}

tasks.jacocoTestReport {
	dependsOn(tasks.test)
	reports {
		xml.required.set(true)
		html.required.set(true)
		csv.required.set(false)
	}
}

tasks.jacocoTestCoverageVerification {
	dependsOn(tasks.jacocoTestReport)
	violationRules {
		rule {
			limit {
				minimum = BigDecimal("0.80")
			}
		}
	}
}

tasks.check {
	dependsOn(tasks.jacocoTestCoverageVerification)
}
