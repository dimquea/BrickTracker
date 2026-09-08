-- Sets by Year Statistics
-- Shows statistics grouped by LEGO set release year

SELECT
    "rebrickable_sets"."year",
    COUNT("bricktracker_sets"."id") AS "total_sets",
    COUNT(DISTINCT "bricktracker_sets"."set") AS "unique_sets",
    SUM("rebrickable_sets"."number_of_parts") AS "total_parts",
    ROUND(AVG("rebrickable_sets"."number_of_parts"), 0) AS "avg_parts_per_set",
    MIN("rebrickable_sets"."number_of_parts") AS "min_parts",
    MAX("rebrickable_sets"."number_of_parts") AS "max_parts",
    -- Financial statistics per year (release year)
    COUNT(CASE WHEN "bricktracker_sets"."purchase_price" IS NOT NULL THEN 1 END) AS "sets_with_price",
    ROUND(SUM("bricktracker_sets"."purchase_price"), 2) AS "total_spent",
    ROUND(AVG("bricktracker_sets"."purchase_price"), 2) AS "avg_price_per_set",
    ROUND(MIN("bricktracker_sets"."purchase_price"), 2) AS "min_price",
    ROUND(MAX("bricktracker_sets"."purchase_price"), 2) AS "max_price",
    -- Problem statistics per year
    COALESCE(SUM("problem_stats"."missing_parts"), 0) AS "missing_parts",
    COALESCE(SUM("problem_stats"."damaged_parts"), 0) AS "damaged_parts",
    -- Minifigure statistics per year
    COALESCE(SUM("minifigure_stats"."minifigure_count"), 0) AS "total_minifigures",
    -- Theme diversity per year
    COUNT(DISTINCT "rebrickable_sets"."theme_id") AS "unique_themes"
FROM "bricktracker_sets"
INNER JOIN "rebrickable_sets" ON "bricktracker_sets"."set" = "rebrickable_sets"."set"
LEFT JOIN (
    SELECT
        "bricktracker_parts"."id",
        SUM("bricktracker_parts"."missing") AS "missing_parts",
        SUM("bricktracker_parts"."damaged") AS "damaged_parts"
    FROM "bricktracker_parts"
    GROUP BY "bricktracker_parts"."id"
) "problem_stats" ON "bricktracker_sets"."id" = "problem_stats"."id"
LEFT JOIN (
    SELECT
        "bricktracker_minifigures"."id",
        SUM(CASE WHEN "bricktracker_minifigures"."alternate" = 0 AND "bricktracker_minifigures"."counterpart" = 0 THEN "bricktracker_minifigures"."quantity" ELSE 0 END) AS "minifigure_count"
    FROM "bricktracker_minifigures"
    GROUP BY "bricktracker_minifigures"."id"
) "minifigure_stats" ON "bricktracker_sets"."id" = "minifigure_stats"."id"
WHERE "rebrickable_sets"."year" IS NOT NULL
GROUP BY "rebrickable_sets"."year"
ORDER BY "rebrickable_sets"."year" DESC