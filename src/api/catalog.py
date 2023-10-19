from fastapi import APIRouter
import sqlalchemy
from src import database as db
from sqlalchemy.exc import DBAPIError

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    catalog = []

    try: 
        with db.engine.begin() as connection:
            # query catalog and ledger_catalog for items in stock
            result = connection.execute(
                sqlalchemy.text(
                    """
                    SELECT c.sku, c.name, l_c.stock, c.price, ARRAY[c.red_ml, c.green_ml, c.blue_ml, c.dark_ml] AS potion_type
                    FROM catalog AS c
                    JOIN (
                        SELECT catalog_id, SUM(change) AS stock
                        FROM ledger_catalog
                        GROUP BY catalog_id
                    ) AS l_c ON c.id = l_c.catalog_id
                    WHERE l_c.stock > 0
                    ORDER BY l_c.stock DESC
                    LIMIT 6
                    """
                ))
            
            # create catalog with queried quantities
            for sku, name, quantity, price, potion_type in result:
                item = {
                    "sku": sku,
                    "name": name,
                    "quantity": quantity,
                    "price": price,
                    "potion_type": potion_type
                }
                catalog.append(item)
    except DBAPIError as error:
        print(f"Error returned: <<<{error}>>>")

    print("catalog:", catalog)

    return catalog
