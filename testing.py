from simulation import CentralProcessingUnit, OperatingSystem, pygame
from datetime import timedelta
from memory import Memory, MemoryUnits
from enums import ProcessPriority
import asyncio


async def add_process_later(os):
    await asyncio.sleep(17)
    os.create_new_process(timedelta(seconds=1), Memory(
        2, MemoryUnits.MB), ProcessPriority.HIGH)
    os.create_new_process(timedelta(seconds=2), Memory(
        2, MemoryUnits.MB), ProcessPriority.LOW)
    os.create_new_process(timedelta(seconds=0.1), Memory(
        2, MemoryUnits.MB), ProcessPriority.IO)
    os.create_new_process(timedelta(seconds=1), Memory(
        2, MemoryUnits.MB), ProcessPriority.HIGH)
    os.create_new_process(timedelta(seconds=2), Memory(
        2, MemoryUnits.MB), ProcessPriority.HIGH)
    os.create_new_process(timedelta(seconds=1.5), Memory(
        2, MemoryUnits.MB), ProcessPriority.LOW)
    os.admit_processes()
    print('Extra processes added')


async def main():
    pygame.init()

    # Create a CPU with a certain memory size (mb) and the operating system (that uses the cpu)
    cpu = CentralProcessingUnit(4000)
    os = OperatingSystem(cpu)

    # Create processes - time to complete, memory taken, priority
    os.create_new_process(
        timedelta(seconds=2), Memory(200000, MemoryUnits.KB), ProcessPriority.IO)
    os.create_new_process(
        timedelta(seconds=2), Memory(123000, MemoryUnits.KB), ProcessPriority.HIGH)
    os.create_new_process(
        timedelta(seconds=2), Memory(200, MemoryUnits.KB), ProcessPriority.HIGH)
    os.create_new_process(
        timedelta(seconds=2), Memory(200000, MemoryUnits.KB), ProcessPriority.HIGH)
    os.create_new_process(
        timedelta(seconds=3), Memory(200000, MemoryUnits.KB), ProcessPriority.HIGH)
    os.create_new_process(
        timedelta(seconds=2), Memory(200000, MemoryUnits.KB), ProcessPriority.LOW)
    os.create_new_process(
        timedelta(seconds=0.5), Memory(200000, MemoryUnits.KB), ProcessPriority.LOW)
    os.create_new_process(
        timedelta(seconds=4), Memory(200000, MemoryUnits.KB), ProcessPriority.LOW)
    os.create_new_process(
        timedelta(seconds=2), Memory(200000, MemoryUnits.KB), ProcessPriority.IO)
    os.create_new_process(
        timedelta(seconds=2), Memory(200000, MemoryUnits.KB), ProcessPriority.IO)

    task1 = asyncio.create_task(os.run())
    task2 = asyncio.create_task(add_process_later(os))

    await task1
    await task2

if __name__ == '__main__':
    asyncio.run(main())
