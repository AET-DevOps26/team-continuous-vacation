# Travel App User Stories

## Story 1: The "Demo User"

**As a** user,

**I want to** access the application immediately using a mock/demo profile,

**So that** I can start planning trips without going through a time-consuming registration process.

**Acceptance Criteria:**

- The frontend bypasses a login screen and injects a randomly generated `user_id` with a demo flag into all API requests.
- The Java backend accepts this `user_id` with a demo flag to associate future database records with this specific demo user.

## Story 2: Initial Trip Generation

**As a** traveler,

**I want to** input my destination (either specific location or general one like beach, or warm), start/end dates, and a specific "vibe" (e.g., Historic, Foodie),

**So that** the system can generate a customized, day-by-day travel itinerary.

**Acceptance Criteria:**

- Frontend has a form for Destination, Dates, and Vibe.
- Java backend successfully passes these parameters to the Python GenAI microservice.
- Python service enforces JSON-mode output from the LLM (e.g using Pydantic/OpenAI Structured Outputs).
- Backend successfully parses the JSON and saves it to the database.

## Story 3: Visual Itinerary Display

**As a** traveler,

**I want to** view my generated itinerary as a structured visual schedule rather than a wall of text,

**So that** I can easily read and understand my daily plan.

**Acceptance Criteria:**

- The UI displays the trip broken down by Days (Day 1, Day 2, etc.).
- Each day is subdivided into Morning, Afternoon, and Evening blocks.
- Each block displays an Activity Title, Description, and Duration.

## Story 4: Regeneration of specific day

**As a** traveler,

**I want to** click on a specific activity block and request a change (e.g., "Make this indoor"),

**So that** I can adjust a single part of my trip without regenerating or breaking the rest of my schedule.

**Acceptance Criteria:**

- Each activity block in the UI has an "Edit/Regenerate" button with a small text prompt input.
- Python GenAI service suggests a single replacement activity formatted as JSON.
- Database updates the specific block and the UI refreshes only that card.

## Story 5: Persistent Trip Storage

**As a** planner,

**I want my** generated itineraries to be saved automatically,

**So that** I can close the browser and return to my trip later without losing data.

**Acceptance Criteria:**

- All generated trips and micro-regenerations are persistently stored in the database.
- Refreshing the frontend page re-fetches the latest state from the Java backend.

## Story 6: Trip Dashboard

**As a** frequent traveler,

**I want to** see a dashboard of all my saved trips upon opening the app,

**So that** I can select which itinerary I want to view or edit.

**Acceptance Criteria:**

- The home screen displays a list or grid of saved trips (showing Destination and Dates).
- Clicking a trip fetches its full itinerary details from the database and loads the Visual Schedule UI.

## Story 7: Delete a trip

**As a** user,

**I want to** delete a trip I no longer plan on taking,

**So that** my dashboard remains clean and relevant.

**Acceptance Criteria:**

- Each trip on the dashboard has a "Delete" option.
- The trip and all its associated daily activities are removed from the database (cascading delete).

## Story 8: Error Handling for AI Hallucinations

**As a** user,

**I want to** be notified gracefully if the AI fails to generate a valid schedule,

**So that** the app doesn't just freeze or crash if the AI acts up.

**Acceptance Criteria:**

- If the Python GenAI service fails to return a valid JSON structure (or times out after 15 seconds), the Java backend catches the error.
- The frontend displays a friendly toast/error message (e.g., "Our AI travel agent got a bit lost. Please try generating again!").
