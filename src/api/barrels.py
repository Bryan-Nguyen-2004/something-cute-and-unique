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
    types = {"SMALL_RED_BARREL":"num_red_", "SMALL_GREEN_BARREL":"num_green_", "SMALL_BLUE_BARREL":"num_blue_"}

    with db.engine.begin() as connection:
        # update ml and gold for every barrel delivered
        for barrel in barrels_delivered:
            sql_update = f'UPDATE global_inventory SET {types[barrel.sku]}ml = {types[barrel.sku]}ml + {barrel.ml_per_barrel * barrel.quantity}, gold = gold - {barrel.price * barrel.quantity}'
            connection.execute(sqlalchemy.text(sql_update))

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    types = {"SMALL_RED_BARREL":"num_red_", "SMALL_GREEN_BARREL":"num_green_", "SMALL_BLUE_BARREL":"num_blue_"}
    ans = []

    with db.engine.begin() as connection:
        # query database
        sql_query = "SELECT gold, num_red_potions, num_blue_potions, num_green_potions FROM global_inventory"
        result = connection.execute(sqlalchemy.text(sql_query))
        first_row = result.first()

        # find corresponding small barrels in catalog
        for barrel in wholesale_catalog:
            if barrel.sku in types:
                # if more then 15 potions or not enough gold then buy nothing
                if getattr(first_row, f'{types[barrel.sku]}potions') >= 15 or first_row.gold < barrel.price or not barrel.quantity:
                    continue
                    
                # add barrel to purchase plan
                ans.append({ "sku": barrel.sku, "quantity": 1 })
    
    return ans
