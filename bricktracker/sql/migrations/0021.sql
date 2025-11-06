-- description: Populate missing image_id values in rebrickable_parts from image URLs
-- Extract image_id from image URL for records with 'elements/' path
-- Note: The url_for_image() method now handles extraction on-the-fly for missing values,
-- so this migration only needs to handle the common case to improve performance

-- For images with 'elements/' in the path, extract the element ID (e.g., 300126 from .../elements/300126.jpg)
UPDATE "rebrickable_parts"
SET "image_id" = SUBSTR(
    "image",
    INSTR("image", 'elements/') + 9,
    INSTR(SUBSTR("image", INSTR("image", 'elements/') + 9), '.') - 1
)
WHERE "image" IS NOT NULL
  AND ("image_id" IS NULL OR "image_id" = '')
  AND "image" LIKE '%elements/%';
