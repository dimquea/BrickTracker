-- Storage Location Statistics
-- Shows statistics grouped by storage location
-- Includes sets, individual parts, individual minifigures, and part lots

WITH

-- Set statistics by storage
set_storage_stats AS (
    SELECT
        "bricktracker_sets"."storage" AS "storage_id",
        COUNT("bricktracker_sets"."id") AS "set_count",
        COUNT(DISTINCT "bricktracker_sets"."set") AS "unique_set_count",
        SUM("rebrickable_sets"."number_of_parts") AS "total_parts",
        COUNT(CASE WHEN "bricktracker_sets"."purchase_price" IS NOT NULL THEN 1 END) AS "sets_with_price",
        ROUND(SUM("bricktracker_sets"."purchase_price"), 2) AS "total_value",
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
    WHERE "bricktracker_sets"."storage" IS NOT NULL
    GROUP BY "bricktracker_sets"."storage"
),

-- Individual part statistics by storage
individual_part_storage_stats AS (
    SELECT
        "storage" AS "storage_id",
        COUNT(*) AS "individual_part_count",
        SUM("quantity") AS "individual_part_quantity",
        SUM("missing") AS "individual_missing_parts",
        SUM("damaged") AS "individual_damaged_parts",
        COUNT(CASE WHEN "purchase_price" IS NOT NULL THEN 1 END) AS "individual_parts_with_price",
        ROUND(SUM("purchase_price"), 2) AS "individual_total_value"
    FROM "bricktracker_individual_parts"
    WHERE "storage" IS NOT NULL AND "lot_id" IS NULL
    GROUP BY "storage"
),

-- Individual minifigure statistics by storage
individual_minifig_storage_stats AS (
    SELECT
        "storage" AS "storage_id",
        COUNT(*) AS "individual_minifig_count",
        SUM("quantity") AS "individual_minifig_quantity",
        COUNT(CASE WHEN "purchase_price" IS NOT NULL THEN 1 END) AS "individual_minifigs_with_price",
        ROUND(SUM("purchase_price"), 2) AS "individual_minifig_total_value"
    FROM "bricktracker_individual_minifigures"
    WHERE "storage" IS NOT NULL
    GROUP BY "storage"
),

-- Part lot statistics by storage
part_lot_storage_stats AS (
    SELECT
        "storage" AS "storage_id",
        COUNT(*) AS "lot_count",
        COUNT(CASE WHEN "purchase_price" IS NOT NULL THEN 1 END) AS "lots_with_price",
        ROUND(SUM("purchase_price"), 2) AS "lot_total_value"
    FROM "bricktracker_individual_part_lots"
    WHERE "storage" IS NOT NULL
    GROUP BY "storage"
)

-- Combine all statistics
SELECT
    COALESCE(sss.storage_id, ipss.storage_id, imss.storage_id, plss.storage_id) AS "storage_id",
    "bricktracker_metadata_storages"."name" AS "storage_name",

    -- Set counts
    COALESCE(sss.set_count, 0) AS "set_count",
    COALESCE(sss.unique_set_count, 0) AS "unique_set_count",

    -- Individual item counts
    COALESCE(ipss.individual_part_count, 0) AS "individual_part_count",
    COALESCE(imss.individual_minifig_count, 0) AS "individual_minifig_count",
    COALESCE(plss.lot_count, 0) AS "lot_count",

    -- Part counts
    COALESCE(sss.total_parts, 0) + COALESCE(ipss.individual_part_quantity, 0) AS "total_parts",
    CASE
        WHEN COALESCE(sss.set_count, 0) > 0
        THEN ROUND(CAST(COALESCE(sss.total_parts, 0) AS FLOAT) / sss.set_count, 0)
        ELSE 0
    END AS "avg_parts_per_set",

    -- Financial statistics
    COALESCE(sss.sets_with_price, 0) + COALESCE(ipss.individual_parts_with_price, 0) +
        COALESCE(imss.individual_minifigs_with_price, 0) + COALESCE(plss.lots_with_price, 0) AS "items_with_price",
    ROUND(COALESCE(sss.total_value, 0) + COALESCE(ipss.individual_total_value, 0) +
        COALESCE(imss.individual_minifig_total_value, 0) + COALESCE(plss.lot_total_value, 0), 2) AS "total_value",
    CASE
        WHEN (COALESCE(sss.sets_with_price, 0) + COALESCE(ipss.individual_parts_with_price, 0) +
              COALESCE(imss.individual_minifigs_with_price, 0) + COALESCE(plss.lots_with_price, 0)) > 0
        THEN ROUND((COALESCE(sss.total_value, 0) + COALESCE(ipss.individual_total_value, 0) +
                    COALESCE(imss.individual_minifig_total_value, 0) + COALESCE(plss.lot_total_value, 0)) /
                   (COALESCE(sss.sets_with_price, 0) + COALESCE(ipss.individual_parts_with_price, 0) +
                    COALESCE(imss.individual_minifigs_with_price, 0) + COALESCE(plss.lots_with_price, 0)), 2)
        ELSE 0
    END AS "avg_price",

    -- Problem statistics
    COALESCE(sss.missing_parts, 0) + COALESCE(ipss.individual_missing_parts, 0) AS "missing_parts",
    COALESCE(sss.damaged_parts, 0) + COALESCE(ipss.individual_damaged_parts, 0) AS "damaged_parts",

    -- Minifigure counts
    COALESCE(sss.total_minifigures, 0) + COALESCE(imss.individual_minifig_quantity, 0) AS "total_minifigures"

FROM set_storage_stats sss
FULL OUTER JOIN individual_part_storage_stats ipss ON sss.storage_id = ipss.storage_id
FULL OUTER JOIN individual_minifig_storage_stats imss ON COALESCE(sss.storage_id, ipss.storage_id) = imss.storage_id
FULL OUTER JOIN part_lot_storage_stats plss ON COALESCE(sss.storage_id, ipss.storage_id, imss.storage_id) = plss.storage_id
LEFT JOIN "bricktracker_metadata_storages" ON COALESCE(sss.storage_id, ipss.storage_id, imss.storage_id, plss.storage_id) = "bricktracker_metadata_storages"."id"

ORDER BY "set_count" DESC, "storage_name" ASC
