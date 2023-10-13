from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/inventory")
def get_inventory():
    """ """

    with db.engine.begin() as connection:
        # query globals
        result = connection.execute(
            sqlalchemy.text(
                "SELECT gold, num_red_ml, num_blue_ml, num_green_ml, num_dark_ml FROM global_inventory"
            )
        )
        gold, num_red_ml, num_blue_ml, num_green_ml, num_dark_ml = result.first()

        # query catalog
        result = connection.execute(
            sqlalchemy.text(
                "SELECT SUM(stock) AS total_stock FROM catalog"
            )
        )

        # calculate totals
        total_potions = result.first().total_stock
        total_ml = num_red_ml + num_blue_ml + num_green_ml + num_dark_ml
    
    return {"number_of_potions": total_potions, "ml_in_barrels": total_ml, "gold": gold}

class Result(BaseModel):
    gold_match: bool
    barrels_match: bool
    potions_match: bool

# Gets called once a day
@router.post("/results")
def post_audit_results(audit_explanation: Result):
    """ """
    print("audit:",audit_explanation)

    return "OK"
