-- Update an existing minifigure during refresh while preserving tracking data
--
-- Отметки пользователя (missing, damaged) не трогаются: обновление
-- приводит в соответствие каталожные данные, а не стирает учёт.
UPDATE "bricktracker_minifigures"
SET
    "quantity" = :quantity,
    "alternate" = :alternate,
    "match_id" = :match_id
WHERE "id" = :id
AND "figure" = :figure
