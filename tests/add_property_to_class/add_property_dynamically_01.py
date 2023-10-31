

class AddPropertyTest:
    def __init__(self):
        self.some_var = 0


AddPropertyTest.__name__ = 'add_property_test'


def managed_attribute(name):
    """Return a property that stores values under a private non-public name."""
    storage_name = '_' + name.lower()

    @property
    def prop(self):
        return getattr(self, storage_name)

    @prop.setter
    def prop(self, value):
        setattr(self, storage_name, value)

    return prop


key = 'thumbnail'

setattr(AddPropertyTest, key, managed_attribute(key))
print(dir(AddPropertyTest))

delattr(AddPropertyTest, key)
print(dir(AddPropertyTest))
