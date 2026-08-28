"""Classic Python gotcha: a class-level (not instance-level) mutable
attribute is shared by every instance of the class.
"""


class Cart:
    def __init__(self):
        self.items = []  # per-instance list; not shared across Cart objects

    def add(self, name, price, qty=1):
        self.items.append({"name": name, "price": price, "qty": qty})

    def total(self):
        return sum(i["price"] * i["qty"] for i in self.items)
