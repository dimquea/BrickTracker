-- description: Add the BrickLink inventory section flags to parts

-- Инвентарь BrickLink делится на секции, и позиция несёт признаки того, в
-- какую она попала. Секция Extra уже отображается существующей колонкой
-- spare, остальные две хранить негде.
--
-- counterpart: позиция получена из другой — например, деталь с наклейкой.
--   Это не дополнительная физическая деталь, а вид уже учтённой, поэтому
--   складывать её количество с основным нельзя.
-- alternate + match_id: взаимозаменяемые позиции, сгруппированные общим
--   match_id. Ноль означает, что позиция ни с чем не сгруппирована.
--
-- Значения по умолчанию соответствуют обычной позиции, поэтому уже
-- импортированные из Rebrickable данные остаются корректными.

BEGIN TRANSACTION;

ALTER TABLE "bricktracker_parts"
ADD COLUMN "counterpart" BOOLEAN NOT NULL DEFAULT 0;

ALTER TABLE "bricktracker_parts"
ADD COLUMN "alternate" BOOLEAN NOT NULL DEFAULT 0;

ALTER TABLE "bricktracker_parts"
ADD COLUMN "match_id" INTEGER NOT NULL DEFAULT 0;

-- Детали отдельных фигурок приходят тем же форматом инвентаря
ALTER TABLE "bricktracker_individual_minifigure_parts"
ADD COLUMN "counterpart" BOOLEAN NOT NULL DEFAULT 0;

ALTER TABLE "bricktracker_individual_minifigure_parts"
ADD COLUMN "alternate" BOOLEAN NOT NULL DEFAULT 0;

ALTER TABLE "bricktracker_individual_minifigure_parts"
ADD COLUMN "match_id" INTEGER NOT NULL DEFAULT 0;

COMMIT;
