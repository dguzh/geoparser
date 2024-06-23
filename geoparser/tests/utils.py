def make_concrete(abstract_class):
    class concreteClass(abstract_class):
        pass

    concreteClass.__abstractmethods__ = set()
    return type("ConcreteClass" + abstract_class.__name__, (concreteClass,), {})
