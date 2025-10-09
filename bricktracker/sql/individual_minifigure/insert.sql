INSERT OR IGNORE INTO "bricktracker_individual_minifigures" (
    "id",
    "figure",
    "quantity",
    "description",
    "storage",
    "purchase_location"
) VALUES (
    :id,
    :figure,
    :quantity,
    :description,
    :storage,
    :purchase_location
)
