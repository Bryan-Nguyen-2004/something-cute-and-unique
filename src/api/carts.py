from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)


class NewCart(BaseModel):
    customer: str

# stored as a dictionary of dictionaries
carts = {}
id_count = 0

@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    global carts
    global id_count
    
    id_count += 1
    carts[id_count] = {}

    return {"cart_id": id_count}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """

    return {}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    global carts
    carts[cart_id][item_sku] = cart_item.quantity

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """

    with db.engine.begin() as connection:

        # check if any potions to sell
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory"))
        first_row = result.first()

        # if no potions then sell nothing
        if not first_row.num_red_potions:
            return {"total_potions_bought": 0, "total_gold_paid": 0}

        # update amount of red ml 
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_potions = num_red_potions - 1"))

        # update amount of gold
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = gold + 50"))

    # the catalog is hard-coded to only ever offer 1 red potion
    return {"total_potions_bought": 1, "total_gold_paid": 50}
