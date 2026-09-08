-- Delete minifigures that weren't in the refresh (no longer in the inventory)
--
-- Проверка на непустую временную таблицу обязательна: без неё сбой на
-- полпути стёр бы все фигурки набора.
DELETE FROM bricktracker_minifigures
WHERE id = :id
AND EXISTS (SELECT 1 FROM temp_refresh_minifigures WHERE id = :id)
AND NOT EXISTS (
    SELECT 1 FROM temp_refresh_minifigures
    WHERE temp_refresh_minifigures.id = bricktracker_minifigures.id
    AND temp_refresh_minifigures.figure = bricktracker_minifigures.figure
)
