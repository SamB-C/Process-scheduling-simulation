from simulation import CentralProcessingUnit, OperatingSystem, pygame
from datetime import timedelta
from memory import Memory, MemoryUnits
from enums import ProcessPriority, PreemptReason
from random import random, randint
import asyncio
from process import Process


def create_process(time_to_complete: timedelta, memory_required: Memory, priority: ProcessPriority) -> Process:
    new_process = Process(time_to_complete, memory_required, priority)
    # Decide whether process should have blocked preemption or not
    blocked_probability = 0.6 if priority == ProcessPriority.IO else 0.1
    random_number = 1 - random()
    if blocked_probability > random_number:
        turns_blocked = randint(3, 7)

        def blocked_func():
            for i in range(turns_blocked):
                yield True
            yield False

        time_to_blocked = random() * time_to_complete

        new_process.add_preemption(
            PreemptReason.BLOCKED, time_to_blocked, blocked_func)
    return new_process


async def add_process_later(os):
    await asyncio.sleep(17)
    processes = [create_process(timedelta(seconds=1), Memory(
        200, MemoryUnits.MB), ProcessPriority.HIGH)]
    processes.append(create_process(timedelta(seconds=1),
                     Memory(2, MemoryUnits.MB), ProcessPriority.HIGH))
    processes.append(create_process(timedelta(seconds=1),
                     Memory(2, MemoryUnits.MB), ProcessPriority.IO))
    processes.append(create_process(timedelta(seconds=1), Memory(
        7.8, MemoryUnits.MB), ProcessPriority.HIGH))
    processes.append(create_process(timedelta(seconds=2),
                     Memory(10, MemoryUnits.MB), ProcessPriority.HIGH))
    processes.append(create_process(timedelta(seconds=1),
                     Memory(200, MemoryUnits.MB), ProcessPriority.LOW))
    processes.append(create_process(timedelta(seconds=1.2),
                     Memory(15, MemoryUnits.MB), ProcessPriority.IO))
    processes.append(create_process(timedelta(seconds=3),
                     Memory(6, MemoryUnits.MB), ProcessPriority.IO))
    processes.append(create_process(timedelta(seconds=2),
                     Memory(8, MemoryUnits.MB), ProcessPriority.IO))
    processes.append(create_process(timedelta(seconds=1),
                     Memory(78, MemoryUnits.MB), ProcessPriority.IO))
    processes.append(create_process(timedelta(seconds=2),
                     Memory(200, MemoryUnits.MB), ProcessPriority.IO))
    os.add_new_processes(*processes)
    os.admit_processes()
    print('Extra processes added')


async def main():
    pygame.init()

    # Create a CPU with a certain memory size (mb) and the operating system (that uses the cpu)
    cpu = CentralProcessingUnit(4000)
    os = OperatingSystem(cpu)

    # Create processes - time to complete, memory taken, priority
    processes = [create_process(timedelta(seconds=1), Memory(
        200, MemoryUnits.MB), ProcessPriority.LOW)]
    processes.append(create_process(timedelta(seconds=1),
                     Memory(2, MemoryUnits.MB), ProcessPriority.LOW))
    processes.append(create_process(timedelta(seconds=4),
                     Memory(2, MemoryUnits.MB), ProcessPriority.IO))
    processes.append(create_process(timedelta(seconds=1.7),
                     Memory(7.8, MemoryUnits.MB), ProcessPriority.HIGH))
    processes.append(create_process(timedelta(seconds=3),
                     Memory(10, MemoryUnits.MB), ProcessPriority.HIGH))
    processes.append(create_process(timedelta(seconds=2), Memory(
        200, MemoryUnits.MB), ProcessPriority.HIGH))
    processes.append(create_process(timedelta(seconds=2),
                     Memory(15, MemoryUnits.MB), ProcessPriority.IO))
    processes.append(create_process(timedelta(seconds=4),
                     Memory(6, MemoryUnits.MB), ProcessPriority.LOW))
    processes.append(create_process(timedelta(seconds=3),
                     Memory(8, MemoryUnits.MB), ProcessPriority.HIGH))
    processes.append(create_process(timedelta(seconds=2),
                     Memory(78, MemoryUnits.MB), ProcessPriority.IO))
    processes.append(create_process(timedelta(seconds=1),
                     Memory(200, MemoryUnits.MB), ProcessPriority.LOW))

    os.add_new_processes(*processes)

    task1 = asyncio.create_task(os.run())
    task2 = asyncio.create_task(add_process_later(os))

    await task1
    await task2

if __name__ == '__main__':
    asyncio.run(main())
