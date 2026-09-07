-- Update existing part quantities during refresh while preserving tracking data
UPDATE "bricktracker_parts"
SET
    "quantity" = :quantity,
    "element" = :element,
    "rebrickable_inventory" = :rebrickable_inventory,
    -- Принадлежность к секциям инвентаря тоже приходит из каталога и может
    -- измениться, поэтому обновляется наравне с количеством. Отметки
    -- пользователя (missing, damaged, checked) при этом не трогаются.
    "counterpart" = :counterpart,
    "alternate" = :alternate,
    "match_id" = :match_id
WHERE "id" = :id
AND "figure" IS NOT DISTINCT FROM :figure
AND "part" = :part
AND "color" = :color
AND "spare" = :spare
