from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from sqlalchemy.exc import IntegrityError

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

    with db.engine.begin() as connection:
        for potion in potions_delivered:
            # destructures potion object
            potion_type = tuple(potion.potion_type)
            quantity = potion.quantity
            red_ml, green_ml, blue_ml, dark_ml = potion_type

            # update catalog inventory
            result = connection.execute(
                sqlalchemy.text(
                    """
                    UPDATE catalog 
                    SET stock = stock + :quantity
                    WHERE 
                    red_ml = :red_ml AND
                    green_ml = :green_ml AND
                    blue_ml = :blue_ml AND
                    dark_ml = :dark_ml
                    RETURNING id
                    """
                ), [{"quantity": quantity, "red_ml": red_ml, "green_ml": green_ml, "blue_ml": blue_ml, "dark_ml": dark_ml}])

            # check to see that one and only one catalog item stock was updated
            if result.rowcount != 1:
                raise IntegrityError("Failed to update catalog item stock")

            # update global inventory
            connection.execute(
                sqlalchemy.text(
                    """
                    UPDATE global_inventory 
                    SET num_red_ml = num_red_ml - :red_ml, 
                    num_green_ml = num_green_ml - :green_ml, 
                    num_blue_ml = num_blue_ml - :blue_ml, 
                    num_dark_ml = num_dark_ml - :dark_ml
                    """
                ), [{"red_ml": red_ml*quantity, "green_ml": green_ml*quantity, "blue_ml": blue_ml*quantity, "dark_ml": dark_ml*quantity}])

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    with db.engine.begin() as connection:
        # query globals
        result = connection.execute(
            sqlalchemy.text(
                """
                SELECT num_red_ml, num_blue_ml, num_green_ml, num_dark_ml 
                FROM global_inventory
                """
            )
        )
        global_red_ml, global_green_ml, global_blue_ml, global_dark_ml = result.first()

        # query catalog 
        result = connection.execute(
            sqlalchemy.text(
                """
                SELECT stock, red_ml, green_ml, blue_ml, dark_ml 
                FROM catalog
                ORDER BY stock
                """
            )
        )
        
        answer = []

        # iterate through every catalog item (lowest stock first)
        for stock, red_ml, green_ml, blue_ml, dark_ml in result:
            # check if enough ml
            if global_red_ml < red_ml or global_green_ml < green_ml or global_blue_ml < blue_ml or global_dark_ml < dark_ml:
                continue

            # calculate how many to make (5 at most)
            amount = 5
            if red_ml > 0: amount = min(amount, global_red_ml // red_ml)
            if green_ml > 0: amount = min(amount, global_green_ml // green_ml)
            if blue_ml > 0: amount = min(amount, global_blue_ml // blue_ml)
            if dark_ml > 0: amount = min(amount, global_dark_ml // dark_ml)
            
            # add to answer if amount > 0
            if amount:
                # update globals
                global_red_ml -= red_ml * amount
                global_green_ml -= green_ml * amount
                global_blue_ml -= blue_ml * amount
                global_dark_ml -= dark_ml * amount

                answer.append(
                    {
                        "potion_type": [red_ml, green_ml, blue_ml, dark_ml],
                        "quantity": amount,
                    }
                )

    return answer
