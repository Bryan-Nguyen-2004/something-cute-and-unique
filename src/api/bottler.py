from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    """ """
    print("potions_delivered:",potions_delivered)

    try:
        with db.engine.begin() as connection:
            # iterate through delivered potions
            for potion in potions_delivered:
                # destructures potion object
                potion_type = tuple(potion.potion_type)
                quantity = potion.quantity
                red_ml, green_ml, blue_ml, dark_ml = potion_type
                ml_changes = []

                # insert transaction w/ description
                result = connection.execute(
                    sqlalchemy.text(
                        "INSERT INTO transactions (description) VALUES (:description) RETURNING id"
                    ), [{"description": f"Received {quantity} {potion_type} potions"}])
                transaction_id = result.scalar_one()

                # append changes to ml_changes
                if red_ml > 0:
                    ml_changes.append({"transaction_id": transaction_id, "type": "red_ml", "change": -(red_ml*quantity)})
                if green_ml > 0:
                    ml_changes.append({"transaction_id": transaction_id, "type": "green_ml", "change": -(green_ml*quantity)})
                if blue_ml > 0:
                    ml_changes.append({"transaction_id": transaction_id, "type": "blue_ml", "change": -(blue_ml*quantity)})
                if dark_ml > 0:
                    ml_changes.append({"transaction_id": transaction_id, "type": "dark_ml", "change": -(dark_ml*quantity)})

                # insert ml changes into global ledger
                connection.execute(
                    sqlalchemy.text(
                        """
                        INSERT INTO ledger_global (transaction_id, type, change)
                        VALUES (:transaction_id, :type, :change)
                        """
                    ), ml_changes)
                
                # query for catalog id
                result = connection.execute(
                    sqlalchemy.text(
                        """
                        SELECT id 
                        FROM catalog 
                        WHERE 
                        red_ml = :red_ml AND
                        green_ml = :green_ml AND
                        blue_ml = :blue_ml AND
                        dark_ml = :dark_ml
                        """
                    ), [{"red_ml": red_ml, "green_ml": green_ml, "blue_ml": blue_ml, "dark_ml": dark_ml}])
                catalog_id = result.scalar_one()
                
                # insert potion stock changes into catalog ledger
                connection.execute(
                    sqlalchemy.text(
                        """
                        INSERT INTO ledger_catalog (transaction_id, catalog_id, change)
                        VALUES (:transaction_id, :type, :change)
                        """
                    ), [{"transaction_id": transaction_id, "catalog_id": catalog_id, "change": quantity}])
    except DBAPIError as error:
        print(f"Error returned: <<<{error}>>>")

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    totals = {}
    ans = []
    
    try:
        with db.engine.begin() as connection:
            # query globals
            result = connection.execute(
                sqlalchemy.text(
                    """
                    SELECT type, SUM(change) AS total 
                    FROM ledger_global 
                    WHERE type != 'gold' 
                    GROUP BY type 
                    ORDER BY type
                    """
                ))

            # destructure globals
            for type, total in result:
                totals[type] = total
            global_blue_ml, global_dark_ml, global_green_ml, global_red_ml = totals.values()

            # query catalog 
            result = connection.execute(
                sqlalchemy.text(
                    """
                    SELECT red_ml, green_ml, blue_ml, dark_ml 
                    FROM catalog
                    ORDER BY stock
                    WHERE dark_ml = 0
                    """
                ))
            
            # iterate through every catalog item (lowest stock first)
            for potion_red_ml, potion_green_ml, potion_blue_ml, potion_dark_ml in result:
                # check if enough ml
                if global_red_ml < potion_red_ml or global_green_ml < potion_green_ml or global_blue_ml < potion_blue_ml or global_dark_ml < potion_dark_ml:
                    continue

                # calculate how many to make (5 at most)
                amount = 8
                if potion_red_ml > 0: amount = min(amount, global_red_ml // potion_red_ml)
                if potion_green_ml > 0: amount = min(amount, global_green_ml // potion_green_ml)
                if potion_blue_ml > 0: amount = min(amount, global_blue_ml // potion_blue_ml)
                if potion_dark_ml > 0: amount = min(amount, global_dark_ml // potion_dark_ml)
                
                # add to answer if amount > 0
                if amount > 0:
                    # update globals
                    global_red_ml -= potion_red_ml * amount
                    global_green_ml -= potion_green_ml * amount
                    global_blue_ml -= potion_blue_ml * amount
                    global_dark_ml -= potion_dark_ml * amount

                    ans.append(
                        {
                            "potion_type": [potion_red_ml, potion_green_ml, potion_blue_ml, potion_dark_ml],
                            "quantity": amount,
                        }
                    )
    except DBAPIError as error:
        print(f"Error returned: <<<{error}>>>")

    print(totals)
    print("plan: ", ans)

    return ans
