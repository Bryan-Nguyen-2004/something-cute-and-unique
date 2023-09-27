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
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_ml = num_red_ml + " + barrel.ml_per_barrel))

            # update amount of gold
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = gold - " + barrel.price))

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    with db.engine.begin() as connection:

        # purchase a new small red potion barrel only if the number of potions in inventory is less than 10 or enough gold
        result_ml = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory"))

        # find small red barrel in catalog
        barrel = None
        for b in wholesale_catalog:
            if b.sku == "SMALL_RED_BARREL":
                barrel = b

        result_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory"))

        # if more then 10 potions or not enough gold then buy nothing
        if result_ml[0] >= 10 or result_gold < barrel.price:
            return []
    
    return [
        {
            "sku": "SMALL_RED_BARREL",
            "quantity": 1,
        }
    ]
