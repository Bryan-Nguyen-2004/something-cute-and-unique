from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from sqlalchemy.exc import DBAPIError

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)


class NewCart(BaseModel):
    customer: str

@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    try:
        with db.engine.begin() as connection:
            # creates new cart
            result = connection.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO carts (customer_name)
                    VALUES (:customer)
                    RETURNING id
                    """
                ), [{"customer": new_cart.customer}])
        
            cart_id = result.first().id
            print("cart_id:", cart_id)
    except DBAPIError as error:
        print(f"Error returned: <<<{error}>>>")

    return {"cart_id": cart_id}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """

    return {}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    try:
        with db.engine.begin() as connection:
            # inserts new item into cart_items
            connection.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO cart_items (cart_id, catalog_id, quantity)
                    SELECT :cart_id, catalog.id, :quantity 
                    FROM catalog 
                    WHERE catalog.sku = :item_sku
                    """
                ), [{"cart_id": cart_id, "quantity": cart_item.quantity, "item_sku": item_sku}])
            
            print(f"added {cart_item.quantity} {item_sku} into cart #{cart_id}")
    except DBAPIError as error:
        print(f"Error returned: <<<{error}>>>")

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    total_gold = 0
    total_potions = 0

    try:    
        with db.engine.begin() as connection:
            # NOTE: joins cart_items, cart, and catalog based on catalog_id
            #       and only includes the rows where cart_id = :cart_id
            result = connection.execute(
                sqlalchemy.text(
                    """
                    SELECT catalog.id, cart_items.quantity, catalog.price, catalog.sku, carts.customer_name
                    FROM cart_items
                    JOIN catalog ON cart_items.catalog_id = catalog.id
                    JOIN carts ON cart_items.cart_id = carts.id
                    WHERE cart_items.cart_id = :cart_id
                    """
                ), [{"cart_id": cart_id}])

            # iterate each item in cart
            for catalog_id, quantity, price, sku, customer_name in result:
                total_gold += price * quantity
                total_potions += quantity

                # insert transaction
                result = connection.execute(
                    sqlalchemy.text(
                        "INSERT INTO transactions (description, cart_id) VALUES (:description, :cart_id) RETURNING id"
                    ), [{"description": f"Sold {quantity} {sku} to {customer_name} for {price} gold each", "cart_id": cart_id}])
                transaction_id = result.scalar_one()

                # update catalog ledger
                connection.execute(
                    sqlalchemy.text(
                        """
                        INSERT INTO ledger_catalog (transaction_id, catalog_id, change)
                        VALUES (:transaction_id, :catalog_id, :change)
                        """
                    ), [{"transaction_id": transaction_id, "catalog_id": catalog_id, "change": -quantity}])
                
                # update global ledger
                connection.execute(
                    sqlalchemy.text(
                        """
                        INSERT INTO ledger_global (transaction_id, type, change)
                        VALUES (:transaction_id, :type, :change)
                        """
                    ), [{"transaction_id": transaction_id, "type": "gold", "change": price*quantity}])
    except DBAPIError as error:
        print(f"Error returned: <<<{error}>>>")

    return {"total_potions_bought": total_potions, "total_gold_paid": total_gold}