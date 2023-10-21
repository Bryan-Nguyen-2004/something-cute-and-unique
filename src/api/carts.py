from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from sqlalchemy.exc import DBAPIError
from enum import Enum

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """
    print("search_page:", search_page)

    metadata = sqlalchemy.MetaData()
    carts = sqlalchemy.Table("carts", metadata, autoload_with=db.engine)
    catalog = sqlalchemy.Table("catalog", metadata, autoload_with=db.engine)
    transactions = sqlalchemy.Table("transactions", metadata, autoload_with=db.engine)
    ledger_global = sqlalchemy.Table("ledger_global", metadata, autoload_with=db.engine)
    ledger_catalog = sqlalchemy.Table("ledger_catalog", metadata, autoload_with=db.engine)

    offset = 0

    if sort_col is search_sort_options.customer_name:
        order_by = carts.c.customer_name
    elif sort_col is search_sort_options.item_sku:
        order_by = catalog.c.sku
    elif sort_col is search_sort_options.line_item_total:
        order_by = ledger_global.c.change
    elif sort_col is search_sort_options.timestamp:
        order_by = transactions.c.created_at
    else:
        assert False

    if sort_order is search_sort_order.asc:
        order_by = sqlalchemy.desc(order_by)
    elif sort_order is search_sort_order.desc:
        order_by = sqlalchemy.asc(order_by)
    else:
        assert False

    stmt = (
        sqlalchemy.select(
            transactions.c.id,
            transactions.c.created_at,
            catalog.c.sku,
            carts.c.customer_name,
            ledger_catalog.c.change,
            catalog.c.price,
        )
        .join(ledger_catalog, ledger_catalog.c.transaction_id == transactions.c.id)
        .join(catalog, catalog.c.id == ledger_catalog.c.catalog_id)
        .join(carts, carts.c.id == transactions.c.cart_id)
        .limit(5)
        .offset(offset)
        .order_by(order_by, transactions.c.id)
    )

    if customer_name != "":
        stmt = stmt.where(carts.c.customer_name.ilike(f"%{customer_name}%"))

    if potion_sku != "":
        stmt = stmt.where(catalog.c.sku.ilike(f"%{potion_sku}%"))

    with db.engine.connect() as connection:
        result = connection.execute(stmt)
        results = []
        i = offset + 1

        for id,created_at,sku,customer_name,change,price in result:
            results.append(
                {
                    "line_item_id": i,
                    "item_sku": str(abs(change)) + " " + sku,
                    "customer_name": customer_name,
                    "line_item_total": abs(change) * price, 
                    "timestamp": created_at,
                }
            )
            i += 1
            
    return {
        "previous": "",
        "next": "",
        "results": results,
    }


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