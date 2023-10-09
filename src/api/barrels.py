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
    print("barrels_delivered:",barrels_delivered)
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
    print("wholesale_catalog:",wholesale_catalog)
    # ex:
    # [Barrel(sku='SMALL_RED_BARREL', ml_per_barrel=500, potion_type=[1, 0, 0, 0], price=100, quantity=10), 
    # Barrel(sku='SMALL_GREEN_BARREL', ml_per_barrel=500, potion_type=[0, 1, 0, 0], price=100, quantity=10), 
    # Barrel(sku='SMALL_BLUE_BARREL', ml_per_barrel=500, potion_type=[0, 0, 1, 0], price=120, quantity=10), 
    # Barrel(sku='MINI_RED_BARREL', ml_per_barrel=200, potion_type=[1, 0, 0, 0], price=60, quantity=1), 
    # Barrel(sku='MINI_GREEN_BARREL', ml_per_barrel=200, potion_type=[0, 1, 0, 0], price=60, quantity=1), 
    # Barrel(sku='MINI_BLUE_BARREL', ml_per_barrel=200, potion_type=[0, 0, 1, 0], price=60, quantity=1)]
    

    # I'm only buying the small barrels
    types = {"SMALL_RED_BARREL":"num_red_", "SMALL_GREEN_BARREL":"num_green_", "SMALL_BLUE_BARREL":"num_blue_"}
    ans = []

    with db.engine.begin() as connection:
        # query database
        sql_query = "SELECT gold, num_red_potions, num_blue_potions, num_green_potions FROM global_inventory"
        result = connection.execute(sqlalchemy.text(sql_query))
        first_row = result.first()
        updated_gold = first_row.gold

        # find corresponding small barrels in catalog
        for barrel in wholesale_catalog:
            if barrel.sku in types:
                # if more then 15 potions or not enough gold then buy nothing
                if getattr(first_row, f'{types[barrel.sku]}potions') >= 15 or updated_gold < barrel.price or not barrel.quantity:
                    continue
                
                updated_gold -= barrel.price

                # add barrel to purchase plan
                ans.append({ "sku": barrel.sku, "quantity": 1 })


    
    return ans
