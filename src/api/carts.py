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

@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
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

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    total_gold = 0
    total_potions = 0

    with db.engine.begin() as connection:
        # NOTE: joins cart_items and catalog based on catalog_id
        #       and only includes the rows where cart_id = :cart_id
        result = connection.execute(
            sqlalchemy.text(
                """
                SELECT cart_items.quantity, catalog.stock, catalog.price
                FROM cart_items
                JOIN catalog ON cart_items.catalog_id = catalog.id
                WHERE cart_items.cart_id = :cart_id
                """
            ), [{"cart_id": cart_id}])

        # iterate each item in cart
        for quantity, stock, price in result:
            # check if enough stock
            if stock < quantity:
                return {"total_potions_bought": 0, "total_gold_paid": 0}
            
            # update totals
            total_gold += price * quantity
            total_potions += quantity

        # NOTE: cross joins cart_items and catalog and filters with conditions
        # join condition - catalog.id = cart_items.catalog_id
        # filter condition - cart_items.cart_id = :cart_id
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE catalog
                SET stock = catalog.stock - cart_items.stock
                FROM cart_items
                WHERE catalog.id = cart_items.catalog_id AND cart_items.cart_id = :cart_id
                """
            ), [{"cart_id": cart_id}])

        # updates gold in global_inventory
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory
                SET gold = gold - :total_gold
                """
                ), [{"total_gold": total_gold}])

    return {"total_potions_bought": total_potions, "total_gold_paid": total_gold}