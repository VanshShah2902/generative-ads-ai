import json
import os

class ProductMemory:
    def __init__(self, path="data/product_memory.json"):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump({"products": []}, f)

    def load(self):
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"products": []}

    def save(self, data):
        with open(self.path, "w") as f:
            json.dump(data, f, indent=4)

    def add_product(self, product):
        data = self.load()
        if "products" not in data:
            data["products"] = []
            
        product_name = product.get("product_name")
        if not product_name:
            return  # Cannot save a product without a name

        # Avoid duplicates and check if already exists to update
        updated = False
        for i, p in enumerate(data["products"]):
            if p.get("product_name") == product_name:
                # Update existing product
                data["products"][i] = product
                updated = True
                break

        if not updated:
            data["products"].append(product)
            
        self.save(data)

    def get_all_products(self):
        return self.load().get("products", [])
