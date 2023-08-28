from enum import Enum


class MemoryUnits(Enum):
    B = 1
    KB = 2
    MB = 3
    GB = 4
    TB = 5


class ProcessStatus(Enum):
    NEW = 1
    READY = 2
    RUNNING = 3
    FINISHED = 4
    BLOCKED = 5


class ProcessPriority(Enum):
    HIGH = 1
    IO = 2
    LOW = 3


priority_colors = {
    ProcessPriority.HIGH: 'Red',
    ProcessPriority.IO: 'Purple',
    ProcessPriority.LOW: 'Blue'
}


class PreemptReason(Enum):
    COMPLETION = 1
    ROUND_ROBIN = 2
    BLOCKED = 3
