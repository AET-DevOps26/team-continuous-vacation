# Database Schema and Persistent Storage

TripTailor uses PostgreSQL for durable application state. The executable schema is
`backend/src/main/resources/schema.sql`; this document is the human-readable
schema and storage reference.

## Runtime Ownership

The backend service owns all application persistence. It connects to PostgreSQL
with Spring JDBC and initializes the schema on startup with
`spring.sql.init.mode=always`. The SQL uses `create table if not exists` and
`create index if not exists`, so startup is idempotent for existing databases.

GenAI, travel-context, frontend, and gateway containers do not write directly to
the database. They interact with persistent trip data through the backend API.

## Local Development Storage

Local development runs PostgreSQL through Docker Compose:

- Service: `db`
- Image: `postgres:17-alpine`
- Database: `triptailor`
- User: `tripuser`
- Host port: `5433` mapped to container port `5432`
- Data volume: `pgdata:/var/lib/postgresql/data`

The named Docker volume `pgdata` keeps database files across container restarts
and `docker compose up --build` runs. Data is removed only when the named volume
is explicitly deleted, for example with `docker compose down -v`.

## Deployed Kubernetes Storage

The Helm chart deploys PostgreSQL as the private `db` service. The database pod
mounts a persistent volume at `/var/lib/postgresql/data` and sets
`PGDATA=/var/lib/postgresql/data/pgdata`.

Relevant Helm values live in `infrastructure/kubernetes/triptailor/values.yaml`:

| Value | Default | Purpose |
| --- | --- | --- |
| `postgres.enabled` | `true` | Deploys the in-cluster PostgreSQL database. |
| `postgres.image.repository` | `postgres` | PostgreSQL image repository. |
| `postgres.image.tag` | `17-alpine` | PostgreSQL image tag. |
| `postgres.auth.database` | `triptailor` | Application database name. |
| `postgres.auth.username` | `tripuser` | Application database user. |
| `postgres.auth.password` | `trippassword` | Default password, overridden by deployment secrets. |
| `postgres.persistence.enabled` | `true` | Uses a PersistentVolumeClaim instead of `emptyDir`. |
| `postgres.persistence.size` | `1Gi` | Requested storage size for the database volume. |
| `postgres.persistence.storageClassName` | `""` | Uses the cluster default storage class unless set. |

When persistence is enabled, the chart creates a PVC named
`<release-name>-postgres` with access mode `ReadWriteOnce`. The Postgres
Deployment uses `strategy: Recreate` so the old pod releases the single-writer
volume before a replacement pod starts.

Check deployed storage with:

```bash
kubectl -n team-continuous-vacation get pvc
kubectl -n team-continuous-vacation describe pvc triptailor-postgres
kubectl -n team-continuous-vacation get deploy/db
```

PVC retention is controlled by the Kubernetes cluster and storage class. Helm
uninstalling the release may leave or remove the PVC depending on cluster policy
and cleanup commands; do not delete the PVC unless the deployed database can be
discarded.

## Entity Relationship Overview

```text
travelers 1 -- * trips 1 -- * days 1 -- * activities 1 -- * activity_tags
```

Deleting a traveler cascades to their trips, days, activities, and tags. Deleting
a trip cascades to its days, activities, and tags. Deleting an activity cascades
to its tags.

## Tables

### `travelers`

Stores registered and demo users.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `uuid` | Primary key | Traveler identifier used by JWT subject claims. |
| `email` | `varchar(320)` | Unique | Nullable for demo travelers. |
| `password_hash` | `varchar(255)` | | Nullable for demo travelers. |
| `is_demo` | `boolean` | Not null | Distinguishes demo sessions from registered accounts. |
| `created_at` | `timestamp with time zone` | Not null | Traveler creation timestamp. |

### `trips`

Stores a traveler's saved trip request and top-level trip metadata.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `uuid` | Primary key | Trip identifier. |
| `traveler_id` | `uuid` | Not null, FK to `travelers(id)` on delete cascade | Owner of the trip. |
| `destination` | `varchar(255)` | Not null | Requested destination. |
| `start_date` | `date` | Not null | First travel day. |
| `end_date` | `date` | Not null | Last travel day. |
| `vibe` | `varchar(255)` | Not null | User preference used for generation. |

Indexes:

- `idx_trips_traveler_id` on `trips(traveler_id)`

### `days`

Stores the generated day-by-day schedule for a trip.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `uuid` | Primary key | Day identifier. |
| `trip_id` | `uuid` | Not null, FK to `trips(id)` on delete cascade | Parent trip. |
| `day_number` | `integer` | Not null | Position in the itinerary. |
| `date` | `date` | Not null | Calendar date for this itinerary day. |

Indexes:

- `idx_days_trip_id` on `days(trip_id)`

### `activities`

Stores individual itinerary activities within a day.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `uuid` | Primary key | Activity identifier. |
| `day_id` | `uuid` | Not null, FK to `days(id)` on delete cascade | Parent day. |
| `time_block` | `varchar(32)` | Not null | Schedule block such as morning, afternoon, or evening. |
| `title` | `varchar(255)` | Not null | Activity title. |
| `description` | `text` | Not null | Generated activity description. |
| `duration_minutes` | `integer` | Not null | Planned activity duration. |
| `is_indoor` | `boolean` | | Nullable when the generated activity does not specify indoor/outdoor status. |

Indexes:

- `idx_activities_day_id` on `activities(day_id)`

### `activity_tags`

Stores zero or more labels for each activity.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `activity_id` | `uuid` | Not null, FK to `activities(id)` on delete cascade | Tagged activity. |
| `tag` | `varchar(64)` | Not null | Activity label. |

Primary key:

- Composite primary key on `(activity_id, tag)`

## Schema Change Process

Update `backend/src/main/resources/schema.sql` and this document together when
the persistent model changes. API shape changes should also be reflected in
`api-specification/frontend.yaml` and the relevant diagrams when they affect
external contracts or architecture.
