-- Track that we've seen this minifigure during refresh
INSERT OR IGNORE INTO temp_refresh_minifigures (id, figure)
VALUES (:id, :figure)
