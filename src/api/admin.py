from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    try:
        with db.engine.begin() as connection:
            # delete all carts, cart_items, transactions, and all ledger entries
            connection.execute(sqlalchemy.text("TRUNCATE transactions CASCADE"))
            connection.execute(sqlalchemy.text("TRUNCATE carts CASCADE"))
            
            # inserts initial values for globals (so they can be queried with WHERE type = 'type')
            result = connection.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO transactions (description)
                    VALUES ('Reset the game state')
                    RETURNING id
                    """
                ))
            transaction_id = result.scalar_one()
            
            connection.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO ledger_global (transaction_id, type, change)
                    VALUES (:transaction_id, :type, :change)
                    """
                ), [{"transaction_id": transaction_id, "type": "gold", "change": 100},
                    {"transaction_id": transaction_id, "type": "red_ml", "change": 0},
                    {"transaction_id": transaction_id, "type": "green_ml", "change": 0},
                    {"transaction_id": transaction_id, "type": "blue_ml", "change": 0}])

    except DBAPIError as error:
        print(f"Error returned: <<<{error}>>>")

    return "OK"


@router.get("/shop_info/")
def get_shop_info():
    """ """

    return {
        "shop_name": "Something Cute and Unique",
        "shop_owner": "Bryan Nguyen",
    }

