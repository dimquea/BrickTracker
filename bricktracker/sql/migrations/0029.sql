-- description: Track missing minifigures and mark inventory alternates

-- Набор нередко достаётся без фигурок, а отметить это было негде: у
-- деталей есть missing и damaged, у фигурок не было ничего. Обходной путь
-- — пометить недостающими все детали фигурки — врёт по смыслу, а для
-- цельнолитых фигурок вроде кубков и микрофигурок не работает вовсе: у
-- них нет деталей, помечать нечего.
--
-- Счётчики, а не флаги, потому что одна и та же фигурка встречается в
-- наборе в нескольких экземплярах, как у деталей.
ALTER TABLE "bricktracker_minifigures"
ADD COLUMN "missing" INTEGER NOT NULL DEFAULT 0;

ALTER TABLE "bricktracker_minifigures"
ADD COLUMN "damaged" INTEGER NOT NULL DEFAULT 0;

-- Секция Alternate инвентаря BrickLink: позиции, сгруппированные общим
-- match_id, взаимозаменяемы, и в наборе присутствует одна из них. У
-- деталей эти колонки появились в миграции 0028, фигуркам они нужны по
-- той же причине — без них альтернатива выглядела как ещё одна фигурка,
-- и набор 3340 показывал четыре штуки вместо трёх.
ALTER TABLE "bricktracker_minifigures"
ADD COLUMN "alternate" BOOLEAN NOT NULL DEFAULT 0;

ALTER TABLE "bricktracker_minifigures"
ADD COLUMN "match_id" INTEGER NOT NULL DEFAULT 0;
