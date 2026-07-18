from app.models.forecast import Forecast

# Mapping of raw materials required per unit of each category
# Structure: { category_name: (silk_yarn_kg, cotton_yarn_kg, dyes_kg) }
MATERIAL_FACTORS = {
    "Silk Saree": (0.6, 0.2, 0.05),
    "Cotton Saree": (0.0, 0.8, 0.03),
    "Stole": (0.1, 0.2, 0.01),
    "Dupatta": (0.3, 0.0, 0.02),
    "Fabric Yardage": (0.0, 0.25, 0.015),
    "Dress Material": (0.2, 0.5, 0.025),
}


def calculate_material_requirements(forecasts: list[Forecast]) -> dict:
    """Ingests forecasts and maps them to aggregate raw material demands."""
    silk_total = 0.0
    cotton_total = 0.0
    dye_total = 0.0

    breakdown = []

    for f in forecasts:
        cat_name = f.category.name if f.category else "Silk Saree"
        qty = f.predicted_demand_index

        # Retrieve conversion factors
        silk_f, cotton_f, dye_f = MATERIAL_FACTORS.get(cat_name, (0.3, 0.3, 0.02))

        # Calculate quantities needed
        s_req = round(qty * silk_f, 2)
        c_req = round(qty * cotton_f, 2)
        d_req = round(qty * dye_f, 2)

        silk_total += s_req
        cotton_total += c_req
        dye_total += d_req

        breakdown.append(
            {
                "category_id": f.category_id,
                "category_name": cat_name,
                "period_start": f.period_start,
                "period_end": f.period_end,
                "quantity": qty,
                "silk_yarn": s_req,
                "cotton_yarn": c_req,
                "dyes": d_req,
            }
        )

    return {
        "silk_yarn": round(silk_total, 2),
        "cotton_yarn": round(cotton_total, 2),
        "dyes": round(dye_total, 2),
        "breakdown": breakdown,
    }
