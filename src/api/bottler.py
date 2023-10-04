from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

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
    print(potions_delivered)
    types = ["num_red_", "num_green_", "num_blue_"]

    with db.engine.begin() as connection:
        for potion in potions_delivered:
            # figure out what potion was delivered
            color = None

            for i in range(3):
                if potion.potion_type[i]:
                    color = types[i]

            if not color: continue

            # update amount of ml and potions
            ml_update = f'UPDATE global_inventory SET {color}ml = {color}ml - {potion.quantity * 100}'
            potion_update = f'UPDATE global_inventory SET {color}potions = {color}potions + {potion.quantity}'
            
            connection.execute(sqlalchemy.text(ml_update))
            connection.execute(sqlalchemy.text(potion_update))

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    with db.engine.begin() as connection:
        # Always mix all available ml if any exists
        sql_query = "SELECT num_red_ml, num_blue_ml, num_green_ml FROM global_inventory ORDER BY "
        result = connection.execute(sqlalchemy.text(sql_query))
        first_row = result.first()

        # calculate amount of potions to create
        red_amount = first_row.num_red_ml // 100
        green_amount = first_row.num_green_ml // 100
        blue_amount = first_row.num_blue_ml // 100

    return [
            {
                "potion_type": [100, 0, 0, 0],
                "quantity": red_amount,
            },
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": green_amount,
            },
            {
                "potion_type": [0, 0, 100, 0],
                "quantity": blue_amount,
            }
        ]
