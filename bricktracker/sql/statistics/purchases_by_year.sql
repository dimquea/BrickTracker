-- Purchases by Year Statistics
-- Shows statistics grouped by purchase year (when you bought items)
-- Includes sets, individual parts, individual minifigures, and part lots

WITH

-- Set purchases by year
set_purchases AS (
    SELECT
        strftime('%Y', datetime("bricktracker_sets"."purchase_date", 'unixepoch')) AS "purchase_year",
        COUNT("bricktracker_sets"."id") AS "total_sets",
        COUNT(DISTINCT "bricktracker_sets"."set") AS "unique_sets",
        SUM("rebrickable_sets"."number_of_parts") AS "total_parts",
        ROUND(AVG("rebrickable_sets"."number_of_parts"), 0) AS "avg_parts_per_set",
        COUNT(CASE WHEN "bricktracker_sets"."purchase_price" IS NOT NULL THEN 1 END) AS "sets_with_price",
        ROUND(SUM("bricktracker_sets"."purchase_price"), 2) AS "sets_total_spent",
        MIN("rebrickable_sets"."year") AS "oldest_set_year",
        MAX("rebrickable_sets"."year") AS "newest_set_year",
        ROUND(AVG("rebrickable_sets"."year"), 0) AS "avg_set_release_year",
        COALESCE(SUM("problem_stats"."missing_parts"), 0) AS "set_missing_parts",
        COALESCE(SUM("problem_stats"."damaged_parts"), 0) AS "set_damaged_parts",
        COALESCE(SUM("minifigure_stats"."minifigure_count"), 0) AS "set_minifigures",
        COALESCE(SUM("minifigure_stats"."unique_minifigures"), 0) AS "set_unique_minifigures",
        COUNT(DISTINCT "rebrickable_sets"."theme_id") AS "unique_themes",
        COUNT(DISTINCT "bricktracker_sets"."purchase_location") AS "set_unique_purchase_locations",
        COUNT(DISTINCT strftime('%m', datetime("bricktracker_sets"."purchase_date", 'unixepoch'))) AS "months_with_purchases"
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
            SUM(CASE WHEN "bricktracker_minifigures"."alternate" = 0 AND "bricktracker_minifigures"."counterpart" = 0 THEN "bricktracker_minifigures"."quantity" ELSE 0 END) AS "minifigure_count",
            COUNT(DISTINCT "bricktracker_minifigures"."figure") AS "unique_minifigures"
        FROM "bricktracker_minifigures"
        GROUP BY "bricktracker_minifigures"."id"
    ) "minifigure_stats" ON "bricktracker_sets"."id" = "minifigure_stats"."id"
    WHERE "bricktracker_sets"."purchase_date" IS NOT NULL
    GROUP BY strftime('%Y', datetime("bricktracker_sets"."purchase_date", 'unixepoch'))
),

-- Individual part purchases by year
individual_part_purchases AS (
    SELECT
        strftime('%Y', datetime("bricktracker_individual_parts"."purchase_date", 'unixepoch')) AS "purchase_year",
        COUNT(*) AS "individual_part_count",
        SUM("bricktracker_individual_parts"."quantity") AS "individual_part_quantity",
        COUNT(DISTINCT "bricktracker_individual_parts"."part" || '-' || "bricktracker_individual_parts"."color") AS "unique_individual_parts",
        SUM("bricktracker_individual_parts"."missing") AS "individual_missing_parts",
        SUM("bricktracker_individual_parts"."damaged") AS "individual_damaged_parts",
        COUNT(CASE WHEN "bricktracker_individual_parts"."purchase_price" IS NOT NULL AND "bricktracker_individual_parts"."lot_id" IS NULL THEN 1 END) AS "individual_parts_with_price",
        ROUND(SUM(CASE WHEN "bricktracker_individual_parts"."lot_id" IS NULL THEN "bricktracker_individual_parts"."purchase_price" END), 2) AS "individual_parts_total_spent",
        COUNT(DISTINCT "bricktracker_individual_parts"."purchase_location") AS "individual_part_unique_purchase_locations"
    FROM "bricktracker_individual_parts"
    WHERE "bricktracker_individual_parts"."purchase_date" IS NOT NULL
    GROUP BY strftime('%Y', datetime("bricktracker_individual_parts"."purchase_date", 'unixepoch'))
),

-- Individual minifigure purchases by year
individual_minifig_purchases AS (
    SELECT
        strftime('%Y', datetime("bricktracker_individual_minifigures"."purchase_date", 'unixepoch')) AS "purchase_year",
        COUNT(*) AS "individual_minifig_count",
        SUM("bricktracker_individual_minifigures"."quantity") AS "individual_minifig_quantity",
        COUNT(DISTINCT "bricktracker_individual_minifigures"."figure") AS "unique_individual_minifigures",
        COUNT(CASE WHEN "bricktracker_individual_minifigures"."purchase_price" IS NOT NULL THEN 1 END) AS "individual_minifigs_with_price",
        ROUND(SUM("bricktracker_individual_minifigures"."purchase_price"), 2) AS "individual_minifigs_total_spent",
        COUNT(DISTINCT "bricktracker_individual_minifigures"."purchase_location") AS "individual_minifig_unique_purchase_locations"
    FROM "bricktracker_individual_minifigures"
    WHERE "bricktracker_individual_minifigures"."purchase_date" IS NOT NULL
    GROUP BY strftime('%Y', datetime("bricktracker_individual_minifigures"."purchase_date", 'unixepoch'))
),

-- Part lot purchases by year
part_lot_purchases AS (
    SELECT
        strftime('%Y', datetime("bricktracker_individual_part_lots"."purchase_date", 'unixepoch')) AS "purchase_year",
        COUNT(*) AS "lot_count",
        COUNT(CASE WHEN "bricktracker_individual_part_lots"."purchase_price" IS NOT NULL THEN 1 END) AS "lots_with_price",
        ROUND(SUM("bricktracker_individual_part_lots"."purchase_price"), 2) AS "lots_total_spent",
        COUNT(DISTINCT "bricktracker_individual_part_lots"."purchase_location") AS "lot_unique_purchase_locations"
    FROM "bricktracker_individual_part_lots"
    WHERE "bricktracker_individual_part_lots"."purchase_date" IS NOT NULL
    GROUP BY strftime('%Y', datetime("bricktracker_individual_part_lots"."purchase_date", 'unixepoch'))
),

-- All purchase years (union of all types)
all_years AS (
    SELECT DISTINCT "purchase_year" FROM set_purchases WHERE "purchase_year" IS NOT NULL
    UNION
    SELECT DISTINCT "purchase_year" FROM individual_part_purchases WHERE "purchase_year" IS NOT NULL
    UNION
    SELECT DISTINCT "purchase_year" FROM individual_minifig_purchases WHERE "purchase_year" IS NOT NULL
    UNION
    SELECT DISTINCT "purchase_year" FROM part_lot_purchases WHERE "purchase_year" IS NOT NULL
)

-- Combine all statistics
SELECT
    ay.purchase_year,

    -- Set counts
    COALESCE(sp.total_sets, 0) AS "total_sets",
    COALESCE(sp.unique_sets, 0) AS "unique_sets",

    -- Individual item counts
    COALESCE(ipp.individual_part_count, 0) AS "individual_part_count",
    COALESCE(imp.individual_minifig_count, 0) AS "individual_minifig_count",
    COALESCE(plp.lot_count, 0) AS "lot_count",

    -- Part counts (unique and total)
    COALESCE(ipp.unique_individual_parts, 0) AS "unique_parts",
    COALESCE(sp.total_parts, 0) + COALESCE(ipp.individual_part_quantity, 0) AS "total_parts",
    COALESCE(sp.avg_parts_per_set, 0) AS "avg_parts_per_set",

    -- Minifigure counts (unique and total)
    COALESCE(sp.set_unique_minifigures, 0) + COALESCE(imp.unique_individual_minifigures, 0) AS "unique_minifigures",
    COALESCE(sp.set_minifigures, 0) + COALESCE(imp.individual_minifig_quantity, 0) AS "total_minifigures",

    -- Financial statistics (combined)
    COALESCE(sp.sets_with_price, 0) + COALESCE(ipp.individual_parts_with_price, 0) +
        COALESCE(imp.individual_minifigs_with_price, 0) + COALESCE(plp.lots_with_price, 0) AS "items_with_price",
    ROUND(COALESCE(sp.sets_total_spent, 0) + COALESCE(ipp.individual_parts_total_spent, 0) +
        COALESCE(imp.individual_minifigs_total_spent, 0) + COALESCE(plp.lots_total_spent, 0), 2) AS "total_spent",

    -- Average, min, max price across all item types for this year
    CASE
        WHEN (COALESCE(sp.sets_with_price, 0) + COALESCE(ipp.individual_parts_with_price, 0) +
              COALESCE(imp.individual_minifigs_with_price, 0) + COALESCE(plp.lots_with_price, 0)) > 0
        THEN ROUND((COALESCE(sp.sets_total_spent, 0) + COALESCE(ipp.individual_parts_total_spent, 0) +
                    COALESCE(imp.individual_minifigs_total_spent, 0) + COALESCE(plp.lots_total_spent, 0)) /
                   (COALESCE(sp.sets_with_price, 0) + COALESCE(ipp.individual_parts_with_price, 0) +
                    COALESCE(imp.individual_minifigs_with_price, 0) + COALESCE(plp.lots_with_price, 0)), 2)
        ELSE 0
    END AS "avg_price_per_item",

    (SELECT MIN(price) FROM (
        SELECT "purchase_price" AS price FROM "bricktracker_sets"
            WHERE "purchase_price" IS NOT NULL
            AND strftime('%Y', datetime("purchase_date", 'unixepoch')) = ay.purchase_year
        UNION ALL
        SELECT "purchase_price" FROM "bricktracker_individual_parts"
            WHERE "purchase_price" IS NOT NULL AND "lot_id" IS NULL
            AND strftime('%Y', datetime("purchase_date", 'unixepoch')) = ay.purchase_year
        UNION ALL
        SELECT "purchase_price" FROM "bricktracker_individual_minifigures"
            WHERE "purchase_price" IS NOT NULL
            AND strftime('%Y', datetime("purchase_date", 'unixepoch')) = ay.purchase_year
        UNION ALL
        SELECT "purchase_price" FROM "bricktracker_individual_part_lots"
            WHERE "purchase_price" IS NOT NULL
            AND strftime('%Y', datetime("purchase_date", 'unixepoch')) = ay.purchase_year
    )) AS "min_price",

    (SELECT MAX(price) FROM (
        SELECT "purchase_price" AS price FROM "bricktracker_sets"
            WHERE "purchase_price" IS NOT NULL
            AND strftime('%Y', datetime("purchase_date", 'unixepoch')) = ay.purchase_year
        UNION ALL
        SELECT "purchase_price" FROM "bricktracker_individual_parts"
            WHERE "purchase_price" IS NOT NULL AND "lot_id" IS NULL
            AND strftime('%Y', datetime("purchase_date", 'unixepoch')) = ay.purchase_year
        UNION ALL
        SELECT "purchase_price" FROM "bricktracker_individual_minifigures"
            WHERE "purchase_price" IS NOT NULL
            AND strftime('%Y', datetime("purchase_date", 'unixepoch')) = ay.purchase_year
        UNION ALL
        SELECT "purchase_price" FROM "bricktracker_individual_part_lots"
            WHERE "purchase_price" IS NOT NULL
            AND strftime('%Y', datetime("purchase_date", 'unixepoch')) = ay.purchase_year
    )) AS "max_price",

    -- Set-specific statistics (for backward compatibility, may be NULL if no sets purchased this year)
    sp.oldest_set_year,
    sp.newest_set_year,
    sp.avg_set_release_year,

    -- Backward compatibility: avg_price_per_set uses combined average (duplicate calculation)
    CASE
        WHEN (COALESCE(sp.sets_with_price, 0) + COALESCE(ipp.individual_parts_with_price, 0) +
              COALESCE(imp.individual_minifigs_with_price, 0) + COALESCE(plp.lots_with_price, 0)) > 0
        THEN ROUND((COALESCE(sp.sets_total_spent, 0) + COALESCE(ipp.individual_parts_total_spent, 0) +
                    COALESCE(imp.individual_minifigs_total_spent, 0) + COALESCE(plp.lots_total_spent, 0)) /
                   (COALESCE(sp.sets_with_price, 0) + COALESCE(ipp.individual_parts_with_price, 0) +
                    COALESCE(imp.individual_minifigs_with_price, 0) + COALESCE(plp.lots_with_price, 0)), 2)
        ELSE 0
    END AS "avg_price_per_set",

    -- Problem statistics
    COALESCE(sp.set_missing_parts, 0) + COALESCE(ipp.individual_missing_parts, 0) AS "missing_parts",
    COALESCE(sp.set_damaged_parts, 0) + COALESCE(ipp.individual_damaged_parts, 0) AS "damaged_parts",

    -- Diversity statistics
    COALESCE(sp.unique_themes, 0) AS "unique_themes",
    (SELECT COUNT(DISTINCT location) FROM (
        SELECT COALESCE(sp.set_unique_purchase_locations, 0) AS location
        UNION
        SELECT COALESCE(ipp.individual_part_unique_purchase_locations, 0)
        UNION
        SELECT COALESCE(imp.individual_minifig_unique_purchase_locations, 0)
        UNION
        SELECT COALESCE(plp.lot_unique_purchase_locations, 0)
    )) AS "unique_purchase_locations",

    COALESCE(sp.months_with_purchases, 0) AS "months_with_purchases"

FROM all_years ay
LEFT JOIN set_purchases sp ON ay.purchase_year = sp.purchase_year
LEFT JOIN individual_part_purchases ipp ON ay.purchase_year = ipp.purchase_year
LEFT JOIN individual_minifig_purchases imp ON ay.purchase_year = imp.purchase_year
LEFT JOIN part_lot_purchases plp ON ay.purchase_year = plp.purchase_year

ORDER BY ay.purchase_year DESC