UPDATE "bricktracker_individual_parts"
SET
    "quantity" = :quantity,
    "description" = :description,
    "storage" = :storage,
    "purchase_location" = :purchase_location,
    "purchase_date" = :purchase_date,
    "purchase_price" = :purchase_price
WHERE "id" = :id
