from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
from src import database as db
import sqlalchemy

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str
    ml_per_barrel: int
    potion_type: list[int]
    price: int
    quantity: int

@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    print("Starting delivery of barrels...")
    for barrel in barrels_delivered:
        # Ensure potion_type has 4 elements
        while len(barrel.potion_type) < 4:
            barrel.potion_type.append(0)

        # Log the barrel data
        print(f"Barrel data: {barrel}")

        with db.engine.begin() as connection:
            sql_query = f"""
            UPDATE global_inventory
            SET num_red_ml = num_red_ml + {barrel.potion_type[0] * barrel.ml_per_barrel * barrel.quantity},
                num_green_ml = num_green_ml + {barrel.potion_type[1] * barrel.ml_per_barrel * barrel.quantity},
                num_blue_ml = num_blue_ml + {barrel.potion_type[2] * barrel.ml_per_barrel * barrel.quantity},
                num_dark_ml = num_dark_ml + {barrel.potion_type[3] * barrel.ml_per_barrel * barrel.quantity}
            """
            # Execute the SQL query and log the result
            result = connection.execute(sqlalchemy.text(sql_query))
            print(f"Inventory update result: {result}")

        print(f"Delivered barrel: {barrel.sku}")
        
    print("Finished delivery of barrels.")
    return "OK"


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    print("Starting wholesale purchase plan...")
    with db.engine.begin() as connection:
        sql_query = """SELECT gold, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM global_inventory"""
        inventory = connection.execute(sqlalchemy.text(sql_query)).first()

    if inventory is None:
        gold, red_ml, green_ml, blue_ml, dark_ml = 0, 0, 0, 0, 0
    else:
        gold, red_ml, green_ml, blue_ml, dark_ml = inventory

    purchase_plan = []

    def buy_potion(potion_type, ml_needed):
        nonlocal gold
        for barrel in wholesale_catalog:
            if barrel.potion_type == potion_type and barrel.price <= gold:
                gold -= barrel.price  # buying only one barrel for now
                purchase_plan.append({"sku": barrel.sku, "quantity": 1})  # quantity is set to 1
                print(f"Bought barrel: {barrel.sku}")
                return barrel.ml_per_barrel  # assuming one barrel is bought, so not multiplying by quantity
        return 0

    if red_ml < 500 and gold > 0:
        red_ml += buy_potion([1, 0, 0, 0], 500 - red_ml)
    if green_ml < 500 and gold > 0:
        green_ml += buy_potion([0, 1, 0, 0], 500 - green_ml)
    if blue_ml < 500 and gold > 0:
        blue_ml += buy_potion([0, 0, 1, 0], 500 - blue_ml)

    # handles the case where any potion is less than 100ml
    # and buys the smallest available barrel that the remaining gold can afford.
    potions = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]  # red, green, blue
    ml_values = [red_ml, green_ml, blue_ml]  # current ml values of potions

    for i, potion in enumerate(potions):
        if ml_values[i] < 100 and gold > 0:
            for barrel in sorted(wholesale_catalog, key=lambda x: x.ml_per_barrel):  # smallest barrel first
                if barrel.potion_type == potion and gold >= barrel.price:
                    purchase_plan.append({"sku": barrel.sku, "quantity": 1})
                    gold -= barrel.price
                    print(f"Bought barrel: {barrel.sku}")
                    break  # break after buying one barrel

    # Update the inventory after all purchases
    with db.engine.begin() as connection:
        sql_query = f"""
        UPDATE global_inventory
        SET gold = {gold},
            num_red_ml = {red_ml},
            num_green_ml = {green_ml},
            num_blue_ml = {blue_ml},
            num_dark_ml = {dark_ml}
        """
        connection.execute(sqlalchemy.text(sql_query))

    print("Finished wholesale purchase plan.")
    return purchase_plan  # returning the purchase plan instead of the inventory statuses

'''
Barrel(sku='SMALL_BLUE_BARREL', ml_per_barrel=500, potion_type=[0, 0, 1, 0], price=120, quantity=1)
Barrel(sku='MINI_BLUE_BARREL', ml_per_barrel=200, potion_type=[0, 0, 1, 0], price=60, quantity=1)]

Barrel(sku='SMALL_GREEN_BARREL', ml_per_barrel=500, potion_type=[0, 1, 0, 0], price=100, quantity=1) 
Barrel(sku='MINI_GREEN_BARREL', ml_per_barrel=200, potion_type=[0, 1, 0, 0], price=60, quantity=1) 
    
'''

'''
OLD FUNCTION:

@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    # Gold value and potion quantities from global_inventory
    with db.engine.begin() as connection:
        sql_query = """SELECT gold, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM global_inventory"""
        inventory = connection.execute(sqlalchemy.text(sql_query)).first()
        gold, red_ml, green_ml, blue_ml, dark_ml = inventory

    wholesale_catalog = sorted(wholesale_catalog, key=lambda x: x.ml_per_barrel)

    res = {}
    # always buy minis
    def buy_potion(potion_type):
        for barrel in wholesale_catalog:
            if barrel.potion_type == potion_type and gold >= barrel.price:
                if barrel.sku in res:
                    res[barrel.sku]["quantity"] += 1
                else:
                    res[barrel.sku] = {"quantity": 1}
                gold -= barrel.price
                break

    if red_ml < 100:
        buy_potion([1, 0, 0, 0])
    if green_ml < 100:
        buy_potion([0, 1, 0, 0])
    if blue_ml < 100:
        buy_potion([0, 0, 1, 0])

    # Iterate through rest of barrels and buy if possible
    for barrel in wholesale_catalog:
        if barrel.price <= gold:
            if barrel.sku in res:
                res[barrel.sku]["quantity"] += 1
            else:
                res[barrel.sku] = {"quantity": 1}
            gold -= barrel.price

    return res



'''

# barrel optimizer function