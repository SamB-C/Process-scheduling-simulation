from enums import MemoryUnits


class Memory:
    def __init__(self, size: int, unit: MemoryUnits):
        self.__size = size
        self.__unit = unit

    def __repr__(self):
        unit = self.__unit.name
        return f'{self.__size}{unit}'

    @property
    def size(self):
        return self.__size

    @size.setter
    def size(self, new_size: int):
        self.__size = new_size

    @property
    def unit(self):
        return self.__unit

    @unit.setter
    def unit(self, unit_to_convert_to: MemoryUnits):
        difference_in_powers = self.unit.value - unit_to_convert_to.value
        self.size = self.size * (1000 ** difference_in_powers)
        self.__unit = unit_to_convert_to

    def __isub__(self, memory_to_deduct):
        memory_to_deduct.unit = self.unit
        self.size = self.size - memory_to_deduct.size
        return self

    def __sub__(self, memory_to_deduct):
        memory_to_deduct.unit = self.unit
        self.size = self.size - memory_to_deduct.size
        return self

    def __iadd__(self, memory_to_add):
        memory_to_add.unit = self.unit
        self.size = self.size + memory_to_add.size
        return self

    def __add__(self, memory_to_add):
        memory_to_add.unit = self.unit
        self.size = self.size + memory_to_add.size
        return self

    def __lt__(self, memory_to_compare):
        previous_unit = memory_to_compare.unit
        memory_to_compare.unit = self.unit
        result = self.size < memory_to_compare.size
        memory_to_compare.unit = previous_unit
        return result
