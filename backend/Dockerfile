# syntax=docker/dockerfile:1.7

FROM eclipse-temurin:21-jdk-alpine AS deps
WORKDIR /workspace
COPY gradlew .
COPY gradle gradle
COPY build.gradle.kts settings.gradle.kts ./
RUN --mount=type=cache,target=/root/.gradle,sharing=locked \
	chmod +x gradlew && \
	./gradlew dependencies --no-daemon

FROM deps AS build
COPY src src
COPY --from=api-spec frontend.yaml src/main/resources/openapi.yaml
RUN --mount=type=cache,target=/root/.gradle,sharing=locked \
	./gradlew bootJar --no-daemon -x test

FROM eclipse-temurin:21-jre-alpine AS runtime
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
COPY --from=build --chown=app:app /workspace/build/libs/*-SNAPSHOT.jar app.jar
USER app
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
