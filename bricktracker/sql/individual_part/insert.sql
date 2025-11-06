INSERT INTO "bricktracker_individual_parts" (
    "id",
    "part",
    "color",
    "quantity",
    "missing",
    "damaged",
    "checked",
    "description",
    "storage",
    "purchase_location",
    "purchase_date",
    "purchase_price"
) VALUES (
    :id,
    :part,
    :color,
    :quantity,
    :missing,
    :damaged,
    :checked,
    :description,
    :storage,
    :purchase_location,
    :purchase_date,
    :purchase_price
)
