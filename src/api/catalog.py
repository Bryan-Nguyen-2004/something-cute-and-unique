from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    with db.engine.begin() as connection:
        # query for values
        sql_query = "SELECT num_red_potions, num_blue_potions, num_green_potions, gold FROM global_inventory"
        result = connection.execute(sqlalchemy.text(sql_query))
        first_row = result.first()

    # create catalog with quered quantities
    catalog = [
        {
            "sku": "RED_POTION_0",
            "name": "red potion",
            "quantity": first_row.num_red_potions,
            "price": 50,
            "potion_type": [100, 0, 0, 0],
        },
        {
            "sku": "GREEN_POTION_0",
            "name": "green potion",
            "quantity": first_row.num_green_potions,
            "price": 50,
            "potion_type": [0, 100, 0, 0],
        }, 
        {
            "sku": "BLUE_POTION_0",
            "name": "blue potion",
            "quantity": first_row.num_blue_potions,
            "price": 50,
            "potion_type": [0, 0, 100, 0],
        }
    ]

    # answer only includes items from catalog with quantity > 0
    answer = []

    for item in catalog:
        if item.quantity:
            answer.append(item)

    return answer
