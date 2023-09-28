from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ """
    print(barrels_delivered)

    with db.engine.begin() as connection:

        for barrel in barrels_delivered:
            # update amount of red ml 
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_ml = num_red_ml + " + str(barrel.ml_per_barrel * barrel.quantity)))

            # update amount of gold
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = gold - " + str(barrel.price * barrel.quantity)))

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    with db.engine.begin() as connection:

        # purchase a new small red potion barrel only if the number of potions in inventory is less than 10 or enough gold
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions,gold FROM global_inventory"))
        first_row = result.first()

        # find small red barrel in catalog
        barrel = None
        for b in wholesale_catalog:
            if b.sku == "SMALL_RED_BARREL":
                barrel = b

        # if more then 10 potions or not enough gold then buy nothing
        if first_row.num_red_potions >= 10 or barrel == None or first_row.gold < barrel.price or not barrel.quantity:
            return []
    
    return [
        {
            "sku": "SMALL_RED_BARREL",
            "quantity": 1,
        }
    ]
