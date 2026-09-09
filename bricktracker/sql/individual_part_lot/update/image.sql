-- Имя файла картинки лота, NULL — своей картинки нет
UPDATE "bricktracker_individual_part_lots"
SET "image" = :image
WHERE "id" = :id
