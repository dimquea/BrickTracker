INSERT OR IGNORE INTO "bricktracker_individual_minifigure_parts" (
    "id",
    "part",
    "color",
    "spare",
    "quantity",
    "element",
    "rebrickable_inventory",
    "missing",
    "damaged",
    "checked"
) VALUES (
    :id,
    :part,
    :color,
    :spare,
    :quantity,
    :element,
    :rebrickable_inventory,
    0,
    0,
    0
)
