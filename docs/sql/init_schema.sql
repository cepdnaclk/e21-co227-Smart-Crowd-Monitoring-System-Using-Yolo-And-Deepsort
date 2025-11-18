-- PostgreSQL schema initialization for Crowd Monitoring System
-- Usage:
--   psql -U postgres -d crowd_monitor -f sql/init_schema.sql

CREATE TABLE IF NOT EXISTS buildings (
  building_id INT PRIMARY KEY,
  building_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crowd_counts (
  id SERIAL PRIMARY KEY,
  building_id INT NOT NULL REFERENCES buildings(building_id) ON DELETE CASCADE,
  current_count INT NOT NULL,
  timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Seed buildings matching default config.json (adjust names as needed)
INSERT INTO buildings (building_id, building_name)
VALUES (1, 'B1'), (3, 'B3')
ON CONFLICT (building_id) DO NOTHING;

-- Example query: latest counts per building
-- SELECT b.building_id, b.building_name, c.current_count, c.timestamp
-- FROM buildings b
-- JOIN LATERAL (
--   SELECT current_count, timestamp FROM crowd_counts c2
--   WHERE c2.building_id = b.building_id
--   ORDER BY timestamp DESC LIMIT 1
-- ) c ON TRUE
-- ORDER BY b.building_id;
