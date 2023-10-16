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
            # query catalog for items in stock
            result = connection.execute(
                sqlalchemy.text(
                    """
                    SELECT sku, name, stock AS quantity, price, ARRAY[red_ml, green_ml, blue_ml, dark_ml] AS potion_type
                    FROM catalog
                    WHERE stock > 0
                    ORDER BY stock DESC
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
