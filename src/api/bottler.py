from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
from src import database as db
import sqlalchemy

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    """ """
    for potion in potions_delivered:
        with db.engine.begin() as connection:
            sql_query = f"""
            UPDATE global_inventory
            SET num_red_potions = num_red_potions + {potion.quantity}
            """
            connection.execute(sqlalchemy.text(sql_query))

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.
    with db.engine.begin() as connection:
        sql_query = """SELECT num_red_ml FROM global_inventory"""
        result = connection.execute(sqlalchemy.text(sql_query))
        num_red_ml = result.first().num_red_ml

        quantity = num_red_ml // 100
        sql_query = f"""
        UPDATE global_inventory
        SET num_red_ml = num_red_ml - {quantity * 100}
        """
        connection.execute(sqlalchemy.text(sql_query))

    return [
            {
                "potion_type": [100, 0, 0, 0],
                "quantity": quantity,
            }
        ]