"""Classic Python gotcha: a class-level (not instance-level) mutable
attribute is shared by every instance of the class.
"""


class Cart:
    items = []  # bug: should be assigned per-instance in __init__

    def add(self, name, price, qty=1):
        self.items.append({"name": name, "price": price, "qty": qty})

    def total(self):
        # MUTANT: ignores quantity entirely.
        return sum(i["price"] for i in self.items)
