UPDATE "bricktracker_individual_minifigures"
SET
    "quantity" = :quantity,
    "description" = :description,
    "storage" = :storage,
    "purchase_location" = :purchase_location
WHERE "id" = :id
