-- Migration 0021: Add existing owner/tag columns to individual minifigure and individual part metadata tables

-- Add owner columns to individual minifigure owners table
ALTER TABLE "bricktracker_individual_minifigure_owners"
ADD COLUMN "owner_32479d0a_cd3c_43c6_aa16_b3f378915b13" BOOLEAN NOT NULL DEFAULT 0;

ALTER TABLE "bricktracker_individual_minifigure_owners"
ADD COLUMN "owner_2f07518d_40e1_4279_b0d0_aa339f195cbf" BOOLEAN NOT NULL DEFAULT 0;

-- Add tag columns to individual minifigure tags table
ALTER TABLE "bricktracker_individual_minifigure_tags"
ADD COLUMN "tag_b1b5c316_5caf_4b82_a085_ac4c7ab9b8db" BOOLEAN NOT NULL DEFAULT 0;

-- Add owner columns to individual part owners table
ALTER TABLE "bricktracker_individual_part_owners"
ADD COLUMN "owner_32479d0a_cd3c_43c6_aa16_b3f378915b13" BOOLEAN NOT NULL DEFAULT 0;

ALTER TABLE "bricktracker_individual_part_owners"
ADD COLUMN "owner_2f07518d_40e1_4279_b0d0_aa339f195cbf" BOOLEAN NOT NULL DEFAULT 0;

-- Add tag columns to individual part tags table
ALTER TABLE "bricktracker_individual_part_tags"
ADD COLUMN "tag_b1b5c316_5caf_4b82_a085_ac4c7ab9b8db" BOOLEAN NOT NULL DEFAULT 0;
