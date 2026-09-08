-- Purchase Location Statistics
-- Shows statistics grouped by purchase location
-- Includes sets, individual parts, individual minifigures, and part lots

WITH

-- Set statistics by purchase location
set_purchase_stats AS (
    SELECT
        "bricktracker_sets"."purchase_location" AS "location_id",
        COUNT("bricktracker_sets"."id") AS "set_count",
        COUNT(DISTINCT "bricktracker_sets"."set") AS "unique_set_count",
        SUM("rebrickable_sets"."number_of_parts") AS "total_parts",
        COUNT(CASE WHEN "bricktracker_sets"."purchase_price" IS NOT NULL THEN 1 END) AS "sets_with_price",
        ROUND(SUM("bricktracker_sets"."purchase_price"), 2) AS "total_spent",
        MIN("bricktracker_sets"."purchase_date") AS "first_purchase",
        MAX("bricktracker_sets"."purchase_date") AS "latest_purchase",
        COALESCE(SUM("problem_stats"."missing_parts"), 0) AS "missing_parts",
        COALESCE(SUM("problem_stats"."damaged_parts"), 0) AS "damaged_parts",
        COALESCE(SUM("minifigure_stats"."minifigure_count"), 0) AS "total_minifigures"
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
    WHERE "bricktracker_sets"."purchase_location" IS NOT NULL
    GROUP BY "bricktracker_sets"."purchase_location"
),

-- Individual part statistics by purchase location
individual_part_purchase_stats AS (
    SELECT
        "purchase_location" AS "location_id",
        COUNT(*) AS "individual_part_count",
        SUM("quantity") AS "individual_part_quantity",
        SUM("missing") AS "individual_missing_parts",
        SUM("damaged") AS "individual_damaged_parts",
        COUNT(CASE WHEN "purchase_price" IS NOT NULL THEN 1 END) AS "individual_parts_with_price",
        ROUND(SUM("purchase_price"), 2) AS "individual_total_spent",
        MIN("purchase_date") AS "individual_first_purchase",
        MAX("purchase_date") AS "individual_latest_purchase"
    FROM "bricktracker_individual_parts"
    WHERE "purchase_location" IS NOT NULL AND "lot_id" IS NULL
    GROUP BY "purchase_location"
),

-- Individual minifigure statistics by purchase location
individual_minifig_purchase_stats AS (
    SELECT
        "purchase_location" AS "location_id",
        COUNT(*) AS "individual_minifig_count",
        SUM("quantity") AS "individual_minifig_quantity",
        COUNT(CASE WHEN "purchase_price" IS NOT NULL THEN 1 END) AS "individual_minifigs_with_price",
        ROUND(SUM("purchase_price"), 2) AS "individual_minifig_total_spent",
        MIN("purchase_date") AS "individual_minifig_first_purchase",
        MAX("purchase_date") AS "individual_minifig_latest_purchase"
    FROM "bricktracker_individual_minifigures"
    WHERE "purchase_location" IS NOT NULL
    GROUP BY "purchase_location"
),

-- Part lot statistics by purchase location
part_lot_purchase_stats AS (
    SELECT
        "purchase_location" AS "location_id",
        COUNT(*) AS "lot_count",
        COUNT(CASE WHEN "purchase_price" IS NOT NULL THEN 1 END) AS "lots_with_price",
        ROUND(SUM("purchase_price"), 2) AS "lot_total_spent",
        MIN("purchase_date") AS "lot_first_purchase",
        MAX("purchase_date") AS "lot_latest_purchase"
    FROM "bricktracker_individual_part_lots"
    WHERE "purchase_location" IS NOT NULL
    GROUP BY "purchase_location"
),

-- Min/Max price calculations (across all item types)
price_stats AS (
    SELECT
        "purchase_location" AS "location_id",
        MIN("purchase_price") AS "min_price",
        MAX("purchase_price") AS "max_price"
    FROM (
        SELECT "purchase_location", "purchase_price" FROM "bricktracker_sets" WHERE "purchase_price" IS NOT NULL
        UNION ALL
        SELECT "purchase_location", "purchase_price" FROM "bricktracker_individual_parts" WHERE "purchase_price" IS NOT NULL AND "lot_id" IS NULL
        UNION ALL
        SELECT "purchase_location", "purchase_price" FROM "bricktracker_individual_minifigures" WHERE "purchase_price" IS NOT NULL
        UNION ALL
        SELECT "purchase_location", "purchase_price" FROM "bricktracker_individual_part_lots" WHERE "purchase_price" IS NOT NULL
    )
    WHERE "purchase_location" IS NOT NULL
    GROUP BY "purchase_location"
)

-- Combine all statistics
SELECT
    COALESCE(sps.location_id, ipps.location_id, imps.location_id, plps.location_id) AS "location_id",
    "bricktracker_metadata_purchase_locations"."name" AS "location_name",

    -- Set counts
    COALESCE(sps.set_count, 0) AS "set_count",
    COALESCE(sps.unique_set_count, 0) AS "unique_set_count",

    -- Individual item counts
    COALESCE(ipps.individual_part_count, 0) AS "individual_part_count",
    COALESCE(imps.individual_minifig_count, 0) AS "individual_minifig_count",
    COALESCE(plps.lot_count, 0) AS "lot_count",

    -- Part counts
    COALESCE(sps.total_parts, 0) + COALESCE(ipps.individual_part_quantity, 0) AS "total_parts",
    CASE
        WHEN COALESCE(sps.set_count, 0) > 0
        THEN ROUND(CAST(COALESCE(sps.total_parts, 0) AS FLOAT) / sps.set_count, 0)
        ELSE 0
    END AS "avg_parts_per_set",

    -- Financial statistics
    COALESCE(sps.sets_with_price, 0) + COALESCE(ipps.individual_parts_with_price, 0) +
        COALESCE(imps.individual_minifigs_with_price, 0) + COALESCE(plps.lots_with_price, 0) AS "items_with_price",
    ROUND(COALESCE(sps.total_spent, 0) + COALESCE(ipps.individual_total_spent, 0) +
        COALESCE(imps.individual_minifig_total_spent, 0) + COALESCE(plps.lot_total_spent, 0), 2) AS "total_spent",
    CASE
        WHEN (COALESCE(sps.sets_with_price, 0) + COALESCE(ipps.individual_parts_with_price, 0) +
              COALESCE(imps.individual_minifigs_with_price, 0) + COALESCE(plps.lots_with_price, 0)) > 0
        THEN ROUND((COALESCE(sps.total_spent, 0) + COALESCE(ipps.individual_total_spent, 0) +
                    COALESCE(imps.individual_minifig_total_spent, 0) + COALESCE(plps.lot_total_spent, 0)) /
                   (COALESCE(sps.sets_with_price, 0) + COALESCE(ipps.individual_parts_with_price, 0) +
                    COALESCE(imps.individual_minifigs_with_price, 0) + COALESCE(plps.lots_with_price, 0)), 2)
        ELSE 0
    END AS "avg_price",
    ROUND(COALESCE(ps.min_price, 0), 2) AS "min_price",
    ROUND(COALESCE(ps.max_price, 0), 2) AS "max_price",

    -- Date range statistics (earliest and latest purchases across all types)
    (SELECT MIN(d) FROM (
        SELECT sps.first_purchase AS d
        UNION ALL SELECT ipps.individual_first_purchase
        UNION ALL SELECT imps.individual_minifig_first_purchase
        UNION ALL SELECT plps.lot_first_purchase
    ) WHERE d IS NOT NULL) AS "first_purchase",
    (SELECT MAX(d) FROM (
        SELECT sps.latest_purchase AS d
        UNION ALL SELECT ipps.individual_latest_purchase
        UNION ALL SELECT imps.individual_minifig_latest_purchase
        UNION ALL SELECT plps.lot_latest_purchase
    ) WHERE d IS NOT NULL) AS "latest_purchase",

    -- Problem statistics
    COALESCE(sps.missing_parts, 0) + COALESCE(ipps.individual_missing_parts, 0) AS "missing_parts",
    COALESCE(sps.damaged_parts, 0) + COALESCE(ipps.individual_damaged_parts, 0) AS "damaged_parts",

    -- Minifigure counts
    COALESCE(sps.total_minifigures, 0) + COALESCE(imps.individual_minifig_quantity, 0) AS "total_minifigures"

FROM set_purchase_stats sps
FULL OUTER JOIN individual_part_purchase_stats ipps ON sps.location_id = ipps.location_id
FULL OUTER JOIN individual_minifig_purchase_stats imps ON COALESCE(sps.location_id, ipps.location_id) = imps.location_id
FULL OUTER JOIN part_lot_purchase_stats plps ON COALESCE(sps.location_id, ipps.location_id, imps.location_id) = plps.location_id
LEFT JOIN price_stats ps ON COALESCE(sps.location_id, ipps.location_id, imps.location_id, plps.location_id) = ps.location_id
LEFT JOIN "bricktracker_metadata_purchase_locations" ON COALESCE(sps.location_id, ipps.location_id, imps.location_id, plps.location_id) = "bricktracker_metadata_purchase_locations"."id"

ORDER BY "set_count" DESC, "location_name" ASC
