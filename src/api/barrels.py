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
    
    global_vals = { "gold":0, (1,0,0,0):0, (0,1,0,0):0, (0,0,1,0):0, (0,0,0,1):0 }
    
    # update global_vals for each barrel delivered
    for barrel in barrels_delivered:
        potion_type = tuple(barrel.potion_type)
        if potion_type not in global_vals: raise Exception(f"Invalid potion type: {potion_type}")

        global_vals[potion_type] += (barrel.ml_per_barrel * barrel.quantity)
        global_vals["gold"] += (barrel.price * barrel.quantity)

    with db.engine.begin() as connection:
        # update global inventory
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory 
                SET gold = gold - :gold, 
                num_red_ml = num_red_ml + :num_red_ml,
                num_green_ml = num_green_ml + :num_green_ml, 
                num_blue_ml = num_blue_ml + :num_blue_ml, 
                num_dark_ml = num_dark_ml + :num_dark_ml
                """
            ), [{"gold": global_vals["gold"], "num_red_ml": global_vals[(1,0,0,0)], "num_green_ml": global_vals[(0,1,0,0)], "num_blue_ml": global_vals[(0,0,1,0)], "num_dark_ml": global_vals[(0,0,0,1)]}])

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
        # query globals
        result = connection.execute(
            sqlalchemy.text(
                "SELECT gold, num_red_ml, num_blue_ml, num_green_ml FROM global_inventory"))
        gold, num_red_ml, num_blue_ml, num_green_ml = result.first()

        # gold is split to buy equal amount of each barrel
        split_gold = gold // 3

        print(gold, num_red_ml, num_blue_ml, num_green_ml, split_gold)

        # find corresponding small barrels in catalog
        for barrel in wholesale_catalog:
            sku, ml_per_barrel, potion_type, price, quantity = barrel
            print(sku, ml_per_barrel, potion_type, price, quantity)

            if sku in types: 
                # calculate amount of barrels to buy
                amount = min(split_gold // price, quantity)
                print("amount:",amount)
                if amount == 0:
                    if gold >= price: amount = 1
                    else: break
                print("updated_amount:",amount)
                gold -= price * amount
                print("gold:",gold)
                if gold < 0: break
                print("updated_gold:",gold)
                # add barrel to purchase plan
                ans.append({ "sku": barrel.sku, "quantity": amount })

    return ans
