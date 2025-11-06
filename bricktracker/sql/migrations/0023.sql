-- description: Add individual part lots system for bulk/cart adding of parts

BEGIN TRANSACTION;

-- Create individual part lots table
CREATE TABLE IF NOT EXISTS "bricktracker_individual_part_lots" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT,
    "description" TEXT,
    "created_date" REAL NOT NULL,
    "storage" TEXT,
    "purchase_location" TEXT,
    "purchase_date" REAL,
    "purchase_price" REAL,
    FOREIGN KEY("storage") REFERENCES "bricktracker_metadata_storages"("id") ON DELETE SET NULL,
    FOREIGN KEY("purchase_location") REFERENCES "bricktracker_metadata_purchase_locations"("id") ON DELETE SET NULL
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS "idx_individual_part_lots_created_date"
ON "bricktracker_individual_part_lots"("created_date");

-- Add missing/damaged/checked fields to individual parts table
ALTER TABLE "bricktracker_individual_parts"
ADD COLUMN "missing" INTEGER NOT NULL DEFAULT 0;

ALTER TABLE "bricktracker_individual_parts"
ADD COLUMN "damaged" INTEGER NOT NULL DEFAULT 0;

ALTER TABLE "bricktracker_individual_parts"
ADD COLUMN "checked" BOOLEAN NOT NULL DEFAULT 0;

-- Add lot_id column to individual parts table
ALTER TABLE "bricktracker_individual_parts"
ADD COLUMN "lot_id" TEXT;

CREATE INDEX IF NOT EXISTS "idx_individual_parts_lot_id"
ON "bricktracker_individual_parts"("lot_id");

-- Create lot owners junction table
CREATE TABLE IF NOT EXISTS "bricktracker_individual_part_lot_owners" (
    "id" TEXT NOT NULL,
    PRIMARY KEY("id"),
    FOREIGN KEY("id") REFERENCES "bricktracker_individual_part_lots"("id") ON DELETE CASCADE
);

-- Create lot tags junction table
CREATE TABLE IF NOT EXISTS "bricktracker_individual_part_lot_tags" (
    "id" TEXT NOT NULL,
    PRIMARY KEY("id"),
    FOREIGN KEY("id") REFERENCES "bricktracker_individual_part_lots"("id") ON DELETE CASCADE
);

COMMIT;
