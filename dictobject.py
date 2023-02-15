class DictObject:
    def __init__(self, d: dict):
        self.d = d

    def get_value(self):
        return self.d

    def __getattr__(self, item: str):
        value = self.d.get(item)
        if isinstance(value, dict):
            return self.__class__(value)
        
        return value

    def __repr__(self):
        return repr(self.d)