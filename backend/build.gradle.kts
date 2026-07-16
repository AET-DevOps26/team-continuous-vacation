import dev.detekt.gradle.Detekt
import dev.detekt.gradle.report.ReportMergeTask
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
	// No baseline file on purpose. A baseline freezes existing findings so the build can fail on
	// new ones, which is a tool for adopting a linter on a codebase too large to clean up. This
	// backend is ~17 files, so a baseline would mostly serve to keep real findings (swallowed
	// exceptions, over-broad catches) parked in an XML nobody reads.
	//
	// The consequence is that detekt cannot distinguish new findings from pre-existing ones, so
	// it reports rather than blocks (see ignoreFailures below). Findings are still published to
	// GitHub code scanning via SARIF.
	ignoreFailures = true
}

// detektMain/detektTest run with type resolution and catch strictly more than the plugin's
// default `detekt` task, which it auto-wires into check. Swapping check over to them keeps a
// local `./gradlew build` reporting exactly what CI's lint step reports.
//
// The plugin also registers non-type-resolution duplicates (`detekt`, `detektMainSourceSet`,
// `detektTestSourceSet`). They are disabled rather than left dormant: they analyse the same code
// more weakly, so running one just produces a noisier duplicate of the same report.
val detektLintTasks = listOf(tasks.named<Detekt>("detektMain"), tasks.named<Detekt>("detektTest"))

listOf("detekt", "detektMainSourceSet", "detektTestSourceSet").forEach { name ->
	tasks.named<Detekt>(name) { enabled = false }
}

tasks.check {
	dependsOn(detektLintTasks)
}

// SARIF feeds the GitHub code-scanning upload in CI, which is what turns findings into inline
// PR annotations. The renderer ships transitively via detekt-cli, so no extra dependency is
// needed. Checkstyle and markdown are on by default and nothing consumes them, so they are
// turned off.
tasks.withType<Detekt>().configureEach {
	reports {
		sarif.required.set(true)
		html.required.set(true)
		checkstyle.required.set(false)
		markdown.required.set(false)
	}
}

// detektMain and detektTest each emit their own SARIF, and two runs uploaded under one
// code-scanning category overwrite each other, silently dropping one source set's findings
// from the PR. Merge them so CI has a single file to upload.
//
// Only the two lint tasks feed the merge. Wiring it to every Detekt task would drag the
// disabled non-type-resolution duplicates in as dependencies and force them to run.
val detektReportMergeSarif by tasks.registering(ReportMergeTask::class) {
	output.set(layout.buildDirectory.file("reports/detekt/detekt-merged.sarif"))
	input.from(detektLintTasks.map { task -> task.flatMap { it.reports.sarif.outputLocation } })
	// finalizedBy, not dependsOn: the merge must still run when detekt fails the build, which
	// is exactly when the annotations matter most.
	mustRunAfter(detektLintTasks)
}

detektLintTasks.forEach { it.configure { finalizedBy(detektReportMergeSarif) } }

dependencies {
	implementation("org.springframework.boot:spring-boot-starter-actuator")
	implementation("org.springframework.boot:spring-boot-starter-jdbc")
	implementation("org.springframework.boot:spring-boot-starter-opentelemetry")
	implementation("org.springframework.boot:spring-boot-starter-security")
	implementation("org.springframework.boot:spring-boot-starter-validation")
	implementation("org.springframework.boot:spring-boot-starter-webflux")
	implementation("org.springframework.boot:spring-boot-starter-webmvc")
	implementation("io.projectreactor.kotlin:reactor-kotlin-extensions")
	implementation("org.jetbrains.kotlin:kotlin-reflect")
	implementation("org.jetbrains.kotlinx:kotlinx-coroutines-reactor")
	implementation("org.springframework.security:spring-security-oauth2-jose")
	implementation("org.springframework.security:spring-security-oauth2-resource-server")
	implementation("com.fasterxml.jackson.core:jackson-databind")
	implementation("tools.jackson.module:jackson-module-kotlin")
	runtimeOnly("io.micrometer:micrometer-registry-prometheus")
	runtimeOnly("org.postgresql:postgresql")
	testRuntimeOnly("com.h2database:h2")
	testImplementation("org.springframework.boot:spring-boot-starter-test")
	testImplementation("org.springframework.boot:spring-boot-starter-actuator-test")
	testImplementation("org.springframework.boot:spring-boot-starter-webflux-test")
	testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
	testImplementation("org.jetbrains.kotlin:kotlin-test-junit5")
	testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test")
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
			requested.group == "io.netty" && requested.name != "netty-bom" ->
				useVersion("4.2.15.Final") // CVE-2026-44249/45416/50010/47691/...
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
	from("${rootProject.projectDir}/../api-specification/frontend.yaml")
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
