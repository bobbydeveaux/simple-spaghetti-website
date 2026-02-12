"""
Initial database schema for F1 Prediction Analytics
Based on the LLD requirements from docs/concepts/f1-prediction-analytics/LLD.md
"""

from sqlalchemy import text
from api.database import engine

# SQL DDL for creating the complete F1 analytics schema
INITIAL_SCHEMA_SQL = """
-- Create drivers table
CREATE TABLE IF NOT EXISTS drivers (
    driver_id SERIAL PRIMARY KEY,
    driver_code VARCHAR(3) UNIQUE NOT NULL,
    driver_name VARCHAR(100) NOT NULL,
    nationality VARCHAR(50),
    date_of_birth DATE,
    current_team_id INTEGER,
    current_elo_rating INTEGER DEFAULT 1500,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for drivers
CREATE INDEX IF NOT EXISTS idx_drivers_code ON drivers(driver_code);
CREATE INDEX IF NOT EXISTS idx_drivers_elo ON drivers(current_elo_rating DESC);

-- Create teams table
CREATE TABLE IF NOT EXISTS teams (
    team_id SERIAL PRIMARY KEY,
    team_name VARCHAR(100) UNIQUE NOT NULL,
    nationality VARCHAR(50),
    current_elo_rating INTEGER DEFAULT 1500,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create circuits table
CREATE TABLE IF NOT EXISTS circuits (
    circuit_id SERIAL PRIMARY KEY,
    circuit_name VARCHAR(100) UNIQUE NOT NULL,
    location VARCHAR(100),
    country VARCHAR(50),
    track_length_km DECIMAL(5, 2),
    track_type VARCHAR(20) CHECK (track_type IN ('street', 'permanent')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create races table
CREATE TABLE IF NOT EXISTS races (
    race_id SERIAL PRIMARY KEY,
    season_year INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    circuit_id INTEGER REFERENCES circuits(circuit_id),
    race_date DATE NOT NULL,
    race_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(season_year, round_number)
);

-- Create indexes for races
CREATE INDEX IF NOT EXISTS idx_races_date ON races(race_date);
CREATE INDEX IF NOT EXISTS idx_races_season ON races(season_year, round_number);
CREATE INDEX IF NOT EXISTS idx_races_status ON races(status);

-- Create race_results table
CREATE TABLE IF NOT EXISTS race_results (
    result_id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(race_id),
    driver_id INTEGER REFERENCES drivers(driver_id),
    team_id INTEGER REFERENCES teams(team_id),
    grid_position INTEGER,
    final_position INTEGER,
    points DECIMAL(4, 1),
    fastest_lap_time INTERVAL,
    status VARCHAR(20) DEFAULT 'finished' CHECK (status IN ('finished', 'retired', 'dnf', 'disqualified')),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(race_id, driver_id)
);

-- Create indexes for race_results
CREATE INDEX IF NOT EXISTS idx_race_results_race ON race_results(race_id);
CREATE INDEX IF NOT EXISTS idx_race_results_driver ON race_results(driver_id);

-- Create qualifying_results table
CREATE TABLE IF NOT EXISTS qualifying_results (
    qualifying_id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(race_id),
    driver_id INTEGER REFERENCES drivers(driver_id),
    q1_time INTERVAL,
    q2_time INTERVAL,
    q3_time INTERVAL,
    final_grid_position INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(race_id, driver_id)
);

-- Create index for qualifying
CREATE INDEX IF NOT EXISTS idx_qualifying_race ON qualifying_results(race_id);

-- Create weather_data table
CREATE TABLE IF NOT EXISTS weather_data (
    weather_id SERIAL PRIMARY KEY,
    race_id INTEGER UNIQUE REFERENCES races(race_id),
    temperature_celsius DECIMAL(4, 1),
    precipitation_mm DECIMAL(5, 2),
    wind_speed_kph DECIMAL(5, 2),
    conditions VARCHAR(20) CHECK (conditions IN ('dry', 'wet', 'mixed')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create predictions table
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(race_id),
    driver_id INTEGER REFERENCES drivers(driver_id),
    predicted_win_probability DECIMAL(5, 2) CHECK (predicted_win_probability >= 0 AND predicted_win_probability <= 100),
    model_version VARCHAR(50) NOT NULL,
    prediction_timestamp TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(race_id, driver_id, model_version)
);

-- Create indexes for predictions
CREATE INDEX IF NOT EXISTS idx_predictions_race ON predictions(race_id);
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(prediction_timestamp DESC);

-- Create prediction_accuracy table
CREATE TABLE IF NOT EXISTS prediction_accuracy (
    accuracy_id SERIAL PRIMARY KEY,
    race_id INTEGER UNIQUE REFERENCES races(race_id),
    brier_score DECIMAL(6, 4),
    log_loss DECIMAL(6, 4),
    correct_winner BOOLEAN,
    top_3_accuracy BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for accuracy
CREATE INDEX IF NOT EXISTS idx_accuracy_race ON prediction_accuracy(race_id);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    username VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Create index for users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Add foreign key constraint for drivers.current_team_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_drivers_team') THEN
        ALTER TABLE drivers ADD CONSTRAINT fk_drivers_team
            FOREIGN KEY (current_team_id) REFERENCES teams(team_id);
    END IF;
END $$;

-- Create materialized view for driver rankings (performance optimization)
DROP MATERIALIZED VIEW IF EXISTS driver_rankings;
CREATE MATERIALIZED VIEW driver_rankings AS
SELECT
    d.driver_id,
    d.driver_name,
    d.current_elo_rating,
    COUNT(CASE WHEN rr.final_position = 1 THEN 1 END) as wins,
    SUM(rr.points) as total_points,
    MAX(r.season_year) as latest_season
FROM drivers d
LEFT JOIN race_results rr ON d.driver_id = rr.driver_id
LEFT JOIN races r ON rr.race_id = r.race_id
GROUP BY d.driver_id, d.driver_name, d.current_elo_rating
ORDER BY d.current_elo_rating DESC;

-- Create unique index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_driver_rankings_driver ON driver_rankings(driver_id);
"""


def create_initial_schema():
    """Create the initial database schema"""
    with engine.connect() as conn:
        # Execute the schema creation SQL
        conn.execute(text(INITIAL_SCHEMA_SQL))
        conn.commit()
        print("Initial F1 Prediction Analytics schema created successfully!")


if __name__ == "__main__":
    create_initial_schema()