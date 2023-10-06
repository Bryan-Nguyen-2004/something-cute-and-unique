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
    print(cart_checkout.payment)

    cart = carts[cart_id]
    types = {"RED_POTION_0":"num_red_", "GREEN_POTION_0":"num_green_", "BLUE_POTION_0":"num_blue_"}
    total_gold = 0
    total_potions = 0
    sql_updates = [] # exists so sql calls only made after I'm sure I have enough potions

    # check if cart exists
    if cart_id not in carts:
        return {"total_potions_bought": 0, "total_gold_paid": 0}

    with db.engine.begin() as connection:
        for sku, quantity in cart.items():
            # check if any potions to sell
            sql_query = f"SELECT {types[sku]}potions FROM global_inventory"
            result = connection.execute(sqlalchemy.text(sql_query))
            first_row = result.first()

            # if not enough potions, then sell nothing (none of the updates to database ran yet)
            if not getattr(first_row, f'{types[sku]}potions'):
                return {"total_potions_bought": 0, "total_gold_paid": 0}
            
            # adds update of potions and gold to list
            sql_update = f"UPDATE global_inventory SET {types[sku]}potions = {types[sku]}potions - {quantity}, gold = gold + {quantity * 50}"
            sql_updates.append(sql_update)

            # update totals (every potion costs 50)
            total_gold += quantity * 50
            total_potions += quantity

        # execute all updates
        for sql_update in sql_updates:
            connection.execute(sqlalchemy.text(sql_update))
    
    # resets cart
    carts[cart_id] = {}

    return {"total_potions_bought": total_potions, "total_gold_paid": total_gold}