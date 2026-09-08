-- Create temporary table to track which minifigures are being refreshed
CREATE TEMPORARY TABLE IF NOT EXISTS temp_refresh_minifigures (
    id TEXT NOT NULL,
    figure TEXT NOT NULL,
    PRIMARY KEY (id, figure)
)
