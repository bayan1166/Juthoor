CREATE TABLE esports_seasons (
	id UUID NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	starts_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	ends_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	reward_gems_top10 INTEGER NOT NULL, 
	reward_coins_participant INTEGER NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE organizations (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	slug VARCHAR(80) NOT NULL, 
	plan_tier plantier NOT NULL, 
	seat_limit INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (slug)
);

CREATE TABLE shop_items (
	id VARCHAR(60) NOT NULL, 
	category VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	gender VARCHAR(10), 
	price_coins INTEGER NOT NULL, 
	price_gems INTEGER NOT NULL, 
	is_premium BOOLEAN NOT NULL, 
	bundle_of VARCHAR(60), 
	season_exclusive BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE esports_challenges (
	id UUID NOT NULL, 
	season_id UUID NOT NULL, 
	skill_id VARCHAR(80) NOT NULL, 
	difficulty INTEGER NOT NULL, 
	question_count INTEGER NOT NULL, 
	time_limit_seconds INTEGER NOT NULL, 
	status challengestatus NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(season_id) REFERENCES esports_seasons (id)
);

CREATE TABLE users (
	id UUID NOT NULL, 
	organization_id UUID, 
	email VARCHAR(255) NOT NULL, 
	hashed_password VARCHAR(255) NOT NULL, 
	full_name VARCHAR(150) NOT NULL, 
	role userrole NOT NULL, 
	guardian_id UUID, 
	grade_level INTEGER NOT NULL, 
	locale VARCHAR(8) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	FOREIGN KEY(guardian_id) REFERENCES users (id)
);

CREATE TABLE attempt_logs (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	skill_id VARCHAR(80) NOT NULL, 
	pattern VARCHAR(40) NOT NULL, 
	difficulty INTEGER NOT NULL, 
	is_correct BOOLEAN NOT NULL, 
	selected_answer TEXT NOT NULL, 
	correct_answer TEXT NOT NULL, 
	misconception TEXT NOT NULL, 
	source VARCHAR(20) NOT NULL, 
	remedial_stage VARCHAR(20) NOT NULL, 
	action VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES users (id)
);

CREATE TABLE avatar_configs (
	student_id UUID NOT NULL, 
	gender VARCHAR(10) NOT NULL, 
	skin VARCHAR(20) NOT NULL, 
	clothing VARCHAR(40) NOT NULL, 
	top VARCHAR(40) NOT NULL, 
	neck VARCHAR(40) NOT NULL, 
	accessories VARCHAR(40) NOT NULL, 
	hair VARCHAR(20) NOT NULL, 
	hair_color VARCHAR(20) NOT NULL, 
	PRIMARY KEY (student_id), 
	FOREIGN KEY(student_id) REFERENCES users (id)
);

CREATE TABLE challenge_attempts (
	id UUID NOT NULL, 
	challenge_id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	correct_count INTEGER NOT NULL, 
	total_count INTEGER NOT NULL, 
	duration_seconds FLOAT NOT NULL, 
	score FLOAT NOT NULL, 
	submitted_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(challenge_id) REFERENCES esports_challenges (id), 
	FOREIGN KEY(student_id) REFERENCES users (id)
);

CREATE TABLE chat_sessions (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	skill_context VARCHAR(80) NOT NULL, 
	started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	ended_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES users (id)
);

CREATE TABLE drill_down_events (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	from_skill VARCHAR(80) NOT NULL, 
	from_pattern VARCHAR(40) NOT NULL, 
	to_skill VARCHAR(80) NOT NULL, 
	to_pattern VARCHAR(40) NOT NULL, 
	depth INTEGER NOT NULL, 
	direction VARCHAR(10) NOT NULL, 
	triggered_by VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES users (id)
);

CREATE TABLE inventory_items (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	item_id VARCHAR(60) NOT NULL, 
	currency_spent currency NOT NULL, 
	price_paid INTEGER NOT NULL, 
	acquired_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_student_item UNIQUE (student_id, item_id), 
	FOREIGN KEY(student_id) REFERENCES users (id), 
	FOREIGN KEY(item_id) REFERENCES shop_items (id)
);

CREATE TABLE skill_mastery (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	skill_id VARCHAR(80) NOT NULL, 
	p_mastery FLOAT NOT NULL, 
	attempts INTEGER NOT NULL, 
	correct INTEGER NOT NULL, 
	status masterystatus NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES users (id)
);

CREATE TABLE student_adaptive_states (
	student_id UUID NOT NULL, 
	current_skill VARCHAR(80) NOT NULL, 
	difficulty INTEGER NOT NULL, 
	consec_wrong INTEGER NOT NULL, 
	total_answered INTEGER NOT NULL, 
	round_answered INTEGER NOT NULL, 
	return_stack JSON NOT NULL, 
	remediation_plan JSON, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (student_id), 
	FOREIGN KEY(student_id) REFERENCES users (id)
);

CREATE TABLE wallet_transactions (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	currency currency NOT NULL, 
	amount INTEGER NOT NULL, 
	balance_after INTEGER NOT NULL, 
	reason txnreason NOT NULL, 
	reference_id VARCHAR(80) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES users (id)
);

CREATE TABLE wallets (
	student_id UUID NOT NULL, 
	coins INTEGER NOT NULL, 
	gems INTEGER NOT NULL, 
	lifetime_coins_earned INTEGER NOT NULL, 
	lifetime_gems_earned INTEGER NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (student_id), 
	FOREIGN KEY(student_id) REFERENCES users (id)
);

CREATE TABLE chat_messages (
	id UUID NOT NULL, 
	session_id UUID NOT NULL, 
	role chatrole NOT NULL, 
	content TEXT NOT NULL, 
	retrieved_chunk_ids JSON NOT NULL, 
	gap_detected BOOLEAN NOT NULL, 
	gap_skill VARCHAR(80) NOT NULL, 
	misconception TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES chat_sessions (id)
);
