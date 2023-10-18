from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from sqlalchemy.exc import DBAPIError

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
    
    types = {(1,0,0,0):"red_ml", (0,1,0,0):"green_ml", (0,0,1,0):"blue_ml", (0,0,0,1):"dark_ml"}

    try:
        with db.engine.begin() as connection:
            # for each barrel delivered
            for barrel in barrels_delivered:
                # calculate changes
                ml_type = types[tuple(barrel.potion_type)]
                ml_change = barrel.ml_per_barrel * barrel.quantity
                gold_change = -(barrel.price * barrel.quantity)
                
                # insert transaction w/ description
                result = connection.execute(
                    sqlalchemy.text(
                        "INSERT INTO transactions (description) VALUES (:description) RETURNING id"
                    ), [{"description": f"Received {barrel.quantity} {barrel.sku}, each costing {barrel.price} gold for {barrel.ml_per_barrel} {ml_type}"}])
                transaction_id = result.scalar_one()

                # insert gold and ml change into global ledger
                connection.execute(
                    sqlalchemy.text(
                        """
                        INSERT INTO ledger_global (transaction_id, type, change)
                        VALUES (:transaction_id, :type, :change)
                        """
                    ), [{"transaction_id": transaction_id, "type": ml_type, "change": ml_change},
                        {"transaction_id": transaction_id, "type": "gold", "change": gold_change}])
    except DBAPIError as error:
        print(f"Error returned: <<<{error}>>>")
        
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
    

    # I'm only buying the small barrels (will likely point to actual barrels in later implementations)
    small_skus = {"SMALL_RED_BARREL": None, "SMALL_GREEN_BARREL": None, "SMALL_BLUE_BARREL": None}
    mini_skus = {"MINI_RED_BARREL": None, "MINI_GREEN_BARREL": None, "MINI_BLUE_BARREL": None}
    totals = {}
    ans = []
    
    try:
        with db.engine.begin() as connection:        
            # query globals
            result = connection.execute(
                sqlalchemy.text(
                    "SELECT type, SUM(change) AS total FROM ledger_global GROUP BY type ORDER BY type"))
            
            # destructure globals
            for type, total in result:
                totals[type] = total
            num_blue_ml, num_dark_ml, gold, num_green_ml, num_red_ml = totals.values()

            # gold is split to buy equal amounts of each barrel
            i = 3
            split_gold = gold // i

            print(gold, num_red_ml, num_blue_ml, num_green_ml, num_dark_ml, split_gold)

            # find corresponding small barrels in catalog
            for barrel in wholesale_catalog:
                sku, ml_per_barrel, potion_type, price, quantity = barrel.sku, barrel.ml_per_barrel, barrel.potion_type, barrel.price, barrel.quantity
                red_ml, green_ml, blue_ml, dark_ml = barrel.potion_type
                print(sku, ml_per_barrel, potion_type, price, quantity)

                if sku in small_skus: 
                    # calculate amount of barrels to buy
                    amount = min(split_gold // price, quantity)

                    if amount == 0:
                        if gold >= price:
                            amount+=1
                            ans.append({ "sku": sku, "quantity": amount })
                        break
                    
                    # update gold
                    gold -= price * amount
                    i -= 1
                    if i > 0: split_gold = gold // i

                    if gold < 0: break

                    # add barrel to purchase plan
                    ans.append({ "sku": sku, "quantity": amount })
    except DBAPIError as error:
        print(f"Error returned: <<<{error}>>>")

    print(totals)
    print("plan: ", ans)

    return ans
