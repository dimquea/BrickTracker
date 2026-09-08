-- Statistics Overview Query
-- Provides statistics for BrickTracker dashboard

WITH
-- Set statistics aggregation
set_stats AS (
    SELECT
        COUNT(*) AS total_sets,
        COUNT(DISTINCT "set") AS unique_sets,
        COUNT(CASE WHEN "purchase_price" IS NOT NULL THEN 1 END) AS sets_with_price,
        ROUND(SUM("purchase_price"), 2) AS total_cost,
        ROUND(AVG("purchase_price"), 2) AS average_cost,
        ROUND(MIN("purchase_price"), 2) AS minimum_cost,
        ROUND(MAX("purchase_price"), 2) AS maximum_cost,
        COUNT(DISTINCT CASE WHEN "storage" IS NOT NULL THEN "storage" END) AS storage_locations_used,
        COUNT(DISTINCT CASE WHEN "purchase_location" IS NOT NULL THEN "purchase_location" END) AS purchase_locations_used,
        COUNT(CASE WHEN "storage" IS NOT NULL THEN 1 END) AS sets_with_storage,
        COUNT(CASE WHEN "purchase_location" IS NOT NULL THEN 1 END) AS sets_with_purchase_location
    FROM "bricktracker_sets"
),

-- Part statistics aggregation (set-based parts)
--
-- Позиции секций Counterpart и Alternate в счёт не идут: первая получена
-- из уже посчитанной детали (наклейка на плитку, детали counterpart-
-- фигурки), вторая заменяет собой основную, а не добавляется к ней.
-- Отметки missing и damaged считаются как есть: их ставил пользователь.
set_part_stats AS (
    SELECT
        COUNT(CASE WHEN "counterpart" = 0 AND "alternate" = 0 THEN 1 END) AS total_part_instances,
        COALESCE(SUM(CASE WHEN "counterpart" = 0 AND "alternate" = 0 THEN "quantity" ELSE 0 END), 0) AS total_parts_count,
        COUNT(DISTINCT CASE WHEN "counterpart" = 0 AND "alternate" = 0 THEN "part" END) AS unique_parts,
        COALESCE(SUM("missing"), 0) AS total_missing_parts,
        COALESCE(SUM("damaged"), 0) AS total_damaged_parts
    FROM "bricktracker_parts"
),

-- Individual part statistics aggregation
individual_part_stats AS (
    SELECT
        COUNT(*) AS total_individual_parts,
        COALESCE(SUM("quantity"), 0) AS total_individual_parts_count,
        COUNT(DISTINCT "part") AS unique_individual_parts,
        COALESCE(SUM("missing"), 0) AS total_missing_individual_parts,
        COALESCE(SUM("damaged"), 0) AS total_damaged_individual_parts,
        COUNT(CASE WHEN "purchase_price" IS NOT NULL AND "lot_id" IS NULL THEN 1 END) AS individual_parts_with_price,
        COALESCE(ROUND(SUM(CASE WHEN "lot_id" IS NULL THEN "purchase_price" END), 2), 0) AS individual_parts_total_cost
    FROM "bricktracker_individual_parts"
),

-- Combined part statistics
part_stats AS (
    SELECT
        set_part_stats.total_part_instances + COALESCE(individual_part_stats.total_individual_parts, 0) AS total_part_instances,
        set_part_stats.total_parts_count + COALESCE(individual_part_stats.total_individual_parts_count, 0) AS total_parts_count,
        (SELECT COUNT(DISTINCT "part") FROM (
            SELECT "part" FROM "bricktracker_parts"
            WHERE "counterpart" = 0 AND "alternate" = 0
            UNION
            SELECT "part" FROM "bricktracker_individual_parts"
        )) AS unique_parts,
        set_part_stats.total_missing_parts + COALESCE(individual_part_stats.total_missing_individual_parts, 0) AS total_missing_parts,
        set_part_stats.total_damaged_parts + COALESCE(individual_part_stats.total_damaged_individual_parts, 0) AS total_damaged_parts
    FROM set_part_stats, individual_part_stats
),

-- Minifigure statistics aggregation (set-based minifigures)
--
-- Как и у деталей, альтернатива и counterpart в счёт не идут: первая
-- заменяет собой основную фигурку набора, второй собран из уже
-- посчитанных деталей.
set_minifig_stats AS (
    SELECT
        COUNT(CASE WHEN "counterpart" = 0 AND "alternate" = 0 THEN 1 END) AS total_minifigure_instances,
        COALESCE(SUM(CASE WHEN "counterpart" = 0 AND "alternate" = 0 THEN "quantity" ELSE 0 END), 0) AS total_minifigures_count,
        COUNT(DISTINCT CASE WHEN "counterpart" = 0 AND "alternate" = 0 THEN "figure" END) AS unique_minifigures
    FROM "bricktracker_minifigures"
),

-- Individual minifigure statistics aggregation
individual_minifig_stats AS (
    SELECT
        COUNT(*) AS total_individual_minifigures,
        COALESCE(SUM("quantity"), 0) AS total_individual_minifigures_count,
        COUNT(DISTINCT "figure") AS unique_individual_minifigures,
        COUNT(CASE WHEN "purchase_price" IS NOT NULL THEN 1 END) AS individual_minifigs_with_price,
        COALESCE(ROUND(SUM("purchase_price"), 2), 0) AS individual_minifigs_total_cost
    FROM "bricktracker_individual_minifigures"
),

-- Combined minifigure statistics
minifig_stats AS (
    SELECT
        set_minifig_stats.total_minifigure_instances + COALESCE(individual_minifig_stats.total_individual_minifigures, 0) AS total_minifigure_instances,
        set_minifig_stats.total_minifigures_count + COALESCE(individual_minifig_stats.total_individual_minifigures_count, 0) AS total_minifigures_count,
        (SELECT COUNT(DISTINCT "figure") FROM (
            SELECT "figure" FROM "bricktracker_minifigures"
            UNION
            SELECT "figure" FROM "bricktracker_individual_minifigures"
        )) AS unique_minifigures
    FROM set_minifig_stats, individual_minifig_stats
),

-- Part lot statistics aggregation
part_lot_stats AS (
    SELECT
        COUNT(*) AS total_part_lots,
        COUNT(CASE WHEN "purchase_price" IS NOT NULL THEN 1 END) AS part_lots_with_price,
        ROUND(SUM("purchase_price"), 2) AS part_lots_total_cost
    FROM "bricktracker_individual_part_lots"
),

-- Combined min/max price across all item types (separate CTE to avoid scalar subquery issues in SQLite)
all_prices AS (
    SELECT "purchase_price" AS price FROM "bricktracker_sets" WHERE "purchase_price" IS NOT NULL AND "purchase_price" != ''
    UNION ALL
    SELECT "purchase_price" FROM "bricktracker_individual_parts" WHERE "purchase_price" IS NOT NULL AND "purchase_price" != '' AND "lot_id" IS NULL
    UNION ALL
    SELECT "purchase_price" FROM "bricktracker_individual_minifigures" WHERE "purchase_price" IS NOT NULL AND "purchase_price" != ''
    UNION ALL
    SELECT "purchase_price" FROM "bricktracker_individual_part_lots" WHERE "purchase_price" IS NOT NULL AND "purchase_price" != ''
),
price_range AS (
    SELECT
        MIN(price) AS combined_minimum_cost,
        MAX(price) AS combined_maximum_cost
    FROM all_prices
),

-- Rebrickable sets count (for sets we actually own)
rebrickable_stats AS (
    SELECT COUNT(*) AS unique_rebrickable_sets
    FROM "rebrickable_sets"
    WHERE "set" IN (SELECT DISTINCT "set" FROM "bricktracker_sets")
),

-- Combined financial statistics
financial_stats AS (
    SELECT
        -- Items with price
        set_stats.sets_with_price +
            COALESCE(individual_part_stats.individual_parts_with_price, 0) +
            COALESCE(individual_minifig_stats.individual_minifigs_with_price, 0) +
            COALESCE(part_lot_stats.part_lots_with_price, 0) AS total_items_with_price,

        -- Total cost across all item types
        ROUND(COALESCE(set_stats.total_cost, 0) +
            COALESCE(individual_part_stats.individual_parts_total_cost, 0) +
            COALESCE(individual_minifig_stats.individual_minifigs_total_cost, 0) +
            COALESCE(part_lot_stats.part_lots_total_cost, 0), 2) AS combined_total_cost,

        -- Average cost across all items with price
        CASE
            WHEN (set_stats.sets_with_price +
                  COALESCE(individual_part_stats.individual_parts_with_price, 0) +
                  COALESCE(individual_minifig_stats.individual_minifigs_with_price, 0) +
                  COALESCE(part_lot_stats.part_lots_with_price, 0)) > 0
            THEN ROUND((COALESCE(set_stats.total_cost, 0) +
                       COALESCE(individual_part_stats.individual_parts_total_cost, 0) +
                       COALESCE(individual_minifig_stats.individual_minifigs_total_cost, 0) +
                       COALESCE(part_lot_stats.part_lots_total_cost, 0)) /
                      (set_stats.sets_with_price +
                       COALESCE(individual_part_stats.individual_parts_with_price, 0) +
                       COALESCE(individual_minifig_stats.individual_minifigs_with_price, 0) +
                       COALESCE(part_lot_stats.part_lots_with_price, 0)), 2)
            ELSE 0
        END AS combined_average_cost,

        -- Min/Max price across all item types
        price_range.combined_minimum_cost,
        price_range.combined_maximum_cost
    FROM set_stats, individual_part_stats, individual_minifig_stats, part_lot_stats, price_range
)

-- Final select combining all statistics
SELECT
    -- Basic counts
    set_stats.total_sets,
    set_stats.unique_sets,
    rebrickable_stats.unique_rebrickable_sets,

    -- Parts statistics
    part_stats.total_part_instances,
    part_stats.total_parts_count,
    part_stats.unique_parts,
    part_stats.total_missing_parts,
    part_stats.total_damaged_parts,

    -- Minifigures statistics
    minifig_stats.total_minifigure_instances,
    minifig_stats.total_minifigures_count,
    minifig_stats.unique_minifigures,

    -- Financial statistics (set-only for backwards compatibility)
    set_stats.sets_with_price,
    set_stats.total_cost,
    set_stats.average_cost,
    set_stats.minimum_cost,
    set_stats.maximum_cost,

    -- Combined financial statistics (all item types)
    financial_stats.total_items_with_price,
    financial_stats.combined_total_cost,
    financial_stats.combined_average_cost,
    financial_stats.combined_minimum_cost,
    financial_stats.combined_maximum_cost,

    -- Storage and location statistics
    set_stats.storage_locations_used,
    set_stats.purchase_locations_used,
    set_stats.sets_with_storage,
    set_stats.sets_with_purchase_location

FROM set_stats, part_stats, minifig_stats, rebrickable_stats, financial_stats