-- F1 Analytics Database Initialization Script
-- This script sets up the basic database structure for local development

-- Create database extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization

-- Create schema
CREATE SCHEMA IF NOT EXISTS f1_analytics;

-- Set default search path
ALTER DATABASE f1_analytics SET search_path TO f1_analytics, public;

-- Create tables (basic structure for development)
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

CREATE TABLE IF NOT EXISTS teams (
    team_id SERIAL PRIMARY KEY,
    team_name VARCHAR(100) UNIQUE NOT NULL,
    nationality VARCHAR(50),
    team_color VARCHAR(7) DEFAULT '#000000',  -- Hex color for UI
    current_elo_rating INTEGER DEFAULT 1500,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS circuits (
    circuit_id SERIAL PRIMARY KEY,
    circuit_name VARCHAR(100) UNIQUE NOT NULL,
    location VARCHAR(100),
    country VARCHAR(50),
    track_length_km DECIMAL(5, 2),
    track_type VARCHAR(20) CHECK (track_type IN ('street', 'permanent')),
    created_at TIMESTAMP DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin'))
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_drivers_code ON drivers(driver_code);
CREATE INDEX IF NOT EXISTS idx_drivers_elo ON drivers(current_elo_rating DESC);
CREATE INDEX IF NOT EXISTS idx_races_date ON races(race_date);
CREATE INDEX IF NOT EXISTS idx_races_season ON races(season_year, round_number);
CREATE INDEX IF NOT EXISTS idx_races_status ON races(status);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Add foreign key constraint
ALTER TABLE drivers ADD CONSTRAINT fk_drivers_team
    FOREIGN KEY (current_team_id) REFERENCES teams(team_id);

-- Insert sample data for development
INSERT INTO teams (team_name, nationality, team_color) VALUES
    ('Red Bull Racing', 'Austria', '#0600EF'),
    ('Ferrari', 'Italy', '#DC143C'),
    ('Mercedes', 'Germany', '#00D2BE'),
    ('McLaren', 'United Kingdom', '#FF8700'),
    ('Alpine', 'France', '#0090FF'),
    ('AlphaTauri', 'Italy', '#2B4562'),
    ('Aston Martin', 'United Kingdom', '#006F62'),
    ('Williams', 'United Kingdom', '#005AFF'),
    ('Alfa Romeo', 'Switzerland', '#900000'),
    ('Haas', 'United States', '#FFFFFF')
ON CONFLICT (team_name) DO NOTHING;

INSERT INTO drivers (driver_code, driver_name, nationality, current_team_id) VALUES
    ('VER', 'Max Verstappen', 'Netherlands', 1),
    ('PER', 'Sergio Perez', 'Mexico', 1),
    ('LEC', 'Charles Leclerc', 'Monaco', 2),
    ('SAI', 'Carlos Sainz', 'Spain', 2),
    ('HAM', 'Lewis Hamilton', 'United Kingdom', 3),
    ('RUS', 'George Russell', 'United Kingdom', 3),
    ('NOR', 'Lando Norris', 'United Kingdom', 4),
    ('PIA', 'Oscar Piastri', 'Australia', 4)
ON CONFLICT (driver_code) DO NOTHING;

INSERT INTO circuits (circuit_name, location, country, track_length_km, track_type) VALUES
    ('Monaco Circuit', 'Monte Carlo', 'Monaco', 3.337, 'street'),
    ('Silverstone Circuit', 'Silverstone', 'United Kingdom', 5.891, 'permanent'),
    ('Spa-Francorchamps', 'Spa', 'Belgium', 7.004, 'permanent'),
    ('Monza Circuit', 'Monza', 'Italy', 5.793, 'permanent'),
    ('Suzuka Circuit', 'Suzuka', 'Japan', 5.807, 'permanent')
ON CONFLICT (circuit_name) DO NOTHING;

-- Create a sample admin user (password: admin123)
INSERT INTO users (email, password_hash, role) VALUES
    ('admin@f1analytics.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewJEeCEWKMPHE7sK', 'admin')
ON CONFLICT (email) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA f1_analytics TO f1user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA f1_analytics TO f1user;