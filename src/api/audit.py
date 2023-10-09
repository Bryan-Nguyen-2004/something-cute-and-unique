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
        # query database
        sql_query = "SELECT gold, num_red_potions, num_red_ml, num_blue_potions, num_blue_ml, num_green_potions, num_green_ml FROM global_inventory"
        result = connection.execute(sqlalchemy.text(sql_query))
        first_row = result.first()

        # calculate totals
        total_potions = first_row.num_red_potions + first_row.num_blue_potions + first_row.num_green_potions
        total_ml = first_row.num_red_ml + first_row.num_blue_ml + first_row.num_green_ml
    
    return {"number_of_potions": total_potions, "ml_in_barrels": total_ml, "gold": first_row.gold}

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
