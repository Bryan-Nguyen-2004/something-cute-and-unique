from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/inventory")
def get_inventory():
    """ """
    try:
        with db.engine.begin() as connection:
            totals = {}
            
            # query globals
            result = connection.execute(
                sqlalchemy.text(
                    "SELECT type, SUM(change) AS total FROM ledger_global GROUP BY type ORDER BY type"))
            
            # destructure globals
            for type, total in result:
                totals[type] = total
            blue_ml, dark_ml, gold, green_ml, red_ml = totals.values()

            # query catalog
            result = connection.execute(
                sqlalchemy.text(
                    "SELECT SUM(change) AS total FROM ledger_catalog"))

            # calculate totals
            total_potions = result.scalar_one()
            total_ml = red_ml + blue_ml + green_ml + dark_ml
    except DBAPIError as error:
        print(f"Error returned: <<<{error}>>>")
    
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
