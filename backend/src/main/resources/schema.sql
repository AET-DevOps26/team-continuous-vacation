create table if not exists travelers (
	id uuid primary key,
	email varchar(320) unique,
	password_hash varchar(255),
	is_demo boolean not null,
	created_at timestamp with time zone not null
);

create table if not exists trips (
	id uuid primary key,
	traveler_id uuid not null references travelers(id) on delete cascade,
	destination varchar(255) not null,
	start_date date not null,
	end_date date not null,
	vibe varchar(255) not null
);

create index if not exists idx_trips_traveler_id on trips(traveler_id);

create table if not exists days (
	id uuid primary key,
	trip_id uuid not null references trips(id) on delete cascade,
	day_number integer not null,
	date date not null
);

create index if not exists idx_days_trip_id on days(trip_id);

create table if not exists activities (
	id uuid primary key,
	day_id uuid not null references days(id) on delete cascade,
	time_block varchar(32) not null,
	title varchar(255) not null,
	description text not null,
	duration_minutes integer not null,
	is_indoor boolean
);

create index if not exists idx_activities_day_id on activities(day_id);

create table if not exists activity_tags (
	activity_id uuid not null references activities(id) on delete cascade,
	tag varchar(64) not null,
	primary key (activity_id, tag)
);
