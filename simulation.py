from memory import MemoryUnits, Memory
from process import Process, ProcessPriority, ProcessStatus, BlockingPreemptionWithPosition, Preemption, pygame, ProcessSurface
from datetime import timedelta
from enums import PreemptReason, priority_colors
import asyncio


class CentralProcessingUnit:
    def __init__(self, total_memory_mb: int):
        self.__total_memory = Memory(total_memory_mb, MemoryUnits.MB)
        self.memory_available = Memory(total_memory_mb, MemoryUnits.MB)
        self.current_process_executing = None

    @property
    def total_memory(self):
        return self.__total_memory


class OperatingSystem:
    def __init__(self, cpu: CentralProcessingUnit, round_robin_timing: timedelta = timedelta(seconds=0.25)):
        # Initalise queues for different states
        # First in first out queue
        self.new_process_queue: list[Process] = []
        # Multiple-level queues (round robin, first in first out, shortest job first)
        self.ready_queue: dict[str: list[Process]] = {
            ProcessPriority.HIGH.name: [],
            ProcessPriority.IO.name: [],
            ProcessPriority.LOW.name: []
        }
        # Only one process at a time (until capacity for multiple cores created)
        self.running_process: list[Process] = []
        # A collection of processes that are finished
        self.finished_processes = []
        # A collection of processes waiting for contested resources
        self.blocked_processes = []

        # Assign the cpu that is being used
        self.CPU = cpu

        # Assign os settings
        self.__round_robin_timing = round_robin_timing

    def create_new_process(self, time_to_complete: timedelta, memory_required: Memory, priority: ProcessPriority):
        '''Creates a new process and adds it to `self.new_process_queue`'''
        self.new_process_queue.append(
            Process(time_to_complete, memory_required, priority))

    def admit_processes(self):
        '''Admits as many processes from `self.new_process_queue` to the `self.ready_queue` as there is space in memory'''
        for index, process in enumerate(self.new_process_queue):
            # If there is space avaiable in memory
            if process.memory_required < self.CPU.memory_available:
                # Change process status, alter available memory and move process to ready
                process_to_move = self.new_process_queue.pop(index)
                process_to_move.status = ProcessStatus.READY
                self.CPU.memory_available -= process_to_move.memory_required
                process_to_move.add_preemption(PreemptReason.COMPLETION)
                self.add_process_to_ready_queue(process_to_move)

    def add_process_to_ready_queue(self, process_to_move: Process) -> None:
        '''Adds the process to the correct list in the ready queue'''
        self.ready_queue[process_to_move.priority.name].append(
            process_to_move)

    def run_process(self):
        '''Moves the next process from ready to running. Sets the time that the process will be preempted at.'''
        self.admit_processes()
        if not self.unfinished_processes:
            # Raise error as there are no processes left to run
            return
        if self.number_ready_processes == 0:
            # The only unfinished processes are currently in the blocked queue
            # Return so blocked processes can be checked during self.run()
            return
        new_running_process = None
        if self.ready_queue_HIGH_priority:
            # Runs the process at the front of the high priority queue
            new_running_process: Process = self.ready_queue_HIGH_priority_pop(
                0)
            # Given preemption reason is round robin
            new_running_process.add_preemption(
                PreemptReason.ROUND_ROBIN, self.round_robin_timing)

        elif self.ready_queue_IO_priority:
            # Runs the process at the front of the I/O priority queue (first process to be added to the queue)
            new_running_process: Process = self.ready_queue_IO_priority_pop(
                0)
        elif self.ready_queue_LOW_priority:
            # Find shortest job
            index_of_shortest_job = 0
            first_process: Process = self.ready_queue_LOW_priority[index_of_shortest_job]
            time_to_complete_shortest_job = first_process.time_to_complete - \
                first_process.cpu_time_recieved
            for index, process in enumerate(self.ready_queue_LOW_priority):
                current_process: Process = process
                cpu_time_needed: timedelta = current_process.time_to_complete - \
                    current_process.cpu_time_recieved
                if cpu_time_needed < time_to_complete_shortest_job:
                    index_of_shortest_job = index
            # Get shortest job
            new_running_process = self.ready_queue_LOW_priority_pop(
                index_of_shortest_job)
        new_running_process.status = ProcessStatus.RUNNING
        self.running_process.append(new_running_process)
        return

    def check_running_process(self):
        '''Checks to see if currently running process (`self.running_process[0]` is complete). If so moves that process to `self.finished_processes` and moves new process into `self.running_process`'''
        # Runs a process if none are currently running
        if len(self.running_process) < 1:
            self.run_process()

        # Move process to correct queue
        current_process = self.running_process.pop()

        # Calculate cpu time recieved by current process
        current_process.calculate_cpu_time_recieved()
        print(
            f'{current_process.cpu_time_recieved}/{current_process.time_to_complete}\t{current_process}')

        if not current_process.cpu_time_over:
            # Process has not reached pre-set time to stop
            if self.process_priority_lower_than_queued_processes(current_process):
                # Currently running process needs to be relpaced with process of higher priority
                # Remove process to ready queue
                current_process.status = ProcessStatus.READY
                self.add_process_to_ready_queue(current_process)
                # Run higher priority process
                self.run_process()
            else:
                # Process can continue running
                self.running_process.append(current_process)
            return

        if current_process.cpu_time_over == PreemptReason.COMPLETION:
            print(f'{current_process} completion')
            # Move process to finished queue
            self.complete_process(current_process)
        elif current_process.cpu_time_over == PreemptReason.ROUND_ROBIN:
            print(f'{current_process} round robin')
            # Remove round robin preemption from process
            for index, preemption in enumerate(current_process.preemptions):
                if preemption.preempt_reason == PreemptReason.ROUND_ROBIN and preemption.is_complete:
                    current_process.remove_preemption(index)
            # Return process to ready queue
            current_process.status = ProcessStatus.READY
            self.add_process_to_ready_queue(current_process)
            # Run new process
        elif current_process.cpu_time_over == PreemptReason.BLOCKED:
            print(f'{current_process} blocked')
            # Move process to blocked queue
            current_process.status = ProcessStatus.BLOCKED
            self.blocked_processes.append(current_process)

        # Run a new process
        self.run_process()

    def complete_process(self, process: Process) -> None:
        '''Takes a process, changes its state to reflect how it is completed, and move to completed collection'''
        process.status = ProcessStatus.FINISHED
        self.finished_processes.append(process)
        self.CPU.memory_available += process.memory_required
        print(f'process complete')

    def check_blocked_processes(self):
        for process_index, process in enumerate(self.blocked_processes):
            process: Process
            blocking_preemptions: list[BlockingPreemptionWithPosition] = process.blocking_preemptions
            for blocking_preemption_index, preemption in blocking_preemptions:
                blocking_preemption_index: int
                preemption: Preemption
                if not preemption.still_blocked:
                    removed_process: Process = self.blocked_processes.pop(
                        process_index)
                    removed_process.remove_preemption(
                        blocking_preemption_index)
                    removed_process.status = ProcessStatus.READY
                    self.add_process_to_ready_queue(removed_process)

    def pygame_create_ready_queue_surfaces(self) -> list[pygame.Surface]:
        '''Creates the HIGH, IO, LOW ready queue surfaces'''
        surfaces = []
        INSET = 5
        BORDER_WIDTH = 2
        FONT_HEIGHT = 35
        QUEUE_NAMES = ['High', 'IO', 'Low']
        font = pygame.font.Font(None, FONT_HEIGHT)
        title_height = 0
        for index, queue in enumerate([self.ready_queue_HIGH_priority, self.ready_queue_IO_priority, self.ready_queue_LOW_priority]):
            color = priority_colors[list(priority_colors.keys())[index]]
            # Calculate width of border box
            width = len(queue) * (Process.PYGAME_SURFACE_WIDTH +
                                  2) + INSET * 2 + BORDER_WIDTH * 2 - 1
            # Create title
            title = font.render(QUEUE_NAMES[index], True, color)
            if index == 0:
                title_height = title.get_height()
            title_width = title.get_width()
            minimum_width = title_width + INSET * 2 + BORDER_WIDTH * 2
            if width < minimum_width:
                width = minimum_width
            # Calculate height of border box
            height = Process.PYGAME_SURFACE_HEIGHT + \
                BORDER_WIDTH * 2 + INSET * 3 + title_height
            # Create border box
            background = pygame.Surface((width, height))
            background.fill(color)
            # Create inside of box
            white_fill = pygame.Surface(
                (width - (BORDER_WIDTH * 2), height - (BORDER_WIDTH * 2)))
            white_fill.fill('White')
            # Add title
            title_position = (
                (white_fill.get_width() - title_width) / 2, INSET)
            white_fill.blit(title, title_position)
            # Add processes to box
            for process_index, process in enumerate(queue):
                process: Process
                process_surface = process.pygame_process_surface.surface
                white_fill.blit(
                    process_surface, ((process_index * (process_surface.get_width() + 1)) + INSET, INSET * 2 + title_height))
            # Add inside of box
            background.blit(white_fill, (BORDER_WIDTH, BORDER_WIDTH))
            # Create list of queues
            surfaces.append(background)
        return surfaces

    def pygame_create_ready_queue_surface(self) -> pygame.Surface:
        '''Creates the ready queue surface to be added to the screen'''
        # Set constants
        GAP = 4
        INSET = 5
        BORDER_WIDTH = 2
        # Create text
        font = pygame.font.Font(None, 40)
        ready_queue_text = font.render('Ready Queue', True, 'Black')
        ready_queue_text_height = ready_queue_text.get_height()
        ready_queue_text_width = ready_queue_text.get_width()
        # Get queue surfaces
        queues = self.pygame_create_ready_queue_surfaces()
        # Calculate dimensions
        width = BORDER_WIDTH + INSET + sum([queue.get_width()
                                            for queue in queues]) + GAP * 2 + INSET + BORDER_WIDTH
        minimum_width = ready_queue_text_width + INSET * 2 + BORDER_WIDTH * 2
        if width < minimum_width:
            width = minimum_width
        height = BORDER_WIDTH + INSET + ready_queue_text_height + \
            INSET + queues[0].get_height() + INSET + BORDER_WIDTH
        # Create border box
        background = pygame.Surface((width, height))
        background.fill('Black')
        # Create white inside
        white_fill = pygame.Surface(
            (width-(BORDER_WIDTH * 2), height-(BORDER_WIDTH * 2)))
        white_fill.fill('White')
        # Add text
        ready_queue_text_position = (
            (white_fill.get_width() - ready_queue_text_width) / 2, INSET)
        white_fill.blit(ready_queue_text, ready_queue_text_position)
        # Add queues
        current_x_pos = INSET
        for queue in queues:
            white_fill.blit(queue, (current_x_pos, INSET *
                            2 + ready_queue_text_height))
            current_x_pos += queue.get_width()
            current_x_pos += GAP
        background.blit(white_fill, (BORDER_WIDTH, BORDER_WIDTH))
        return background

    def pygame_create_memory_text(self) -> pygame.Surface:
        '''Create the text that displays how much available memory the CPU has'''
        GAP = 4
        # Create text
        memory_text = pygame.font.Font(None, 35)
        available_memory_text = memory_text.render(
            'Available Memory:', True, 'Black')
        available_memory_result_text = memory_text.render(
            self.CPU.memory_available.__repr__(), True, 'Black')
        available_memory_text_width = available_memory_text.get_width()
        available_memory_result_text_width = available_memory_result_text.get_width()
        # Calculate dimensions
        width = available_memory_text_width
        if available_memory_text_width < available_memory_result_text_width:
            width = available_memory_result_text_width
        height = available_memory_text.get_height(
        ) + available_memory_result_text.get_height() + GAP
        # Create background
        background = pygame.Surface((width, height))
        background.fill('White')
        # Add text to background
        available_memory_text_position = (
            (width - available_memory_text_width) / 2, 0)
        background.blit(available_memory_text, available_memory_text_position)
        available_memory_result_text_position = (
            (width - available_memory_result_text_width) / 2, available_memory_text.get_height() + GAP)
        background.blit(available_memory_result_text,
                        available_memory_result_text_position)
        return background

    def create_blank_process(self) -> pygame.Surface:
        '''Creates a rectangle the size of a process'''
        background = pygame.Surface(
            (Process.PYGAME_SURFACE_WIDTH, Process.PYGAME_SURFACE_HEIGHT))
        background.fill('Black')
        white_inside = pygame.Surface(
            (Process.PYGAME_SURFACE_WIDTH - 2, Process.PYGAME_SURFACE_HEIGHT - 2))
        white_inside.fill('White')
        background.blit(white_inside, (1, 1))
        return background

    def pygame_create_cpu_surface(self) -> pygame.Surface:
        '''Creates the CPU surface'''
        INSET = 10
        BORDER_WIDTH = 3
        GAP = 15
        # Create text
        title_font = pygame.font.Font(None, 40)
        title = title_font.render('CPU', True, 'Black')
        memory_text = self.pygame_create_memory_text()
        # Calculate dimensions
        width = BORDER_WIDTH + INSET + Process.PYGAME_SURFACE_WIDTH + \
            GAP + memory_text.get_width() + INSET + BORDER_WIDTH
        height = BORDER_WIDTH + INSET + \
            title.get_height() + GAP + Process.PYGAME_SURFACE_HEIGHT + INSET + BORDER_WIDTH
        # Create background
        background = pygame.Surface((width, height))
        background.fill('Black')
        # Create white inside
        white_inside = pygame.Surface(
            (width - (BORDER_WIDTH * 2), height - (BORDER_WIDTH * 2)))
        white_inside.fill('White')
        # Add contents
        x_pos = INSET
        y_pos = INSET
        title_position = (((width - (BORDER_WIDTH * 2)) -
                          title.get_width()) / 2, y_pos)
        white_inside.blit(title, title_position)
        y_pos += title.get_height() + GAP
        running_process_slot = self.create_blank_process()
        if self.running_process:
            running_process_slot = self.running_process[0].pygame_process_surface.surface
        white_inside.blit(running_process_slot, (x_pos, y_pos))
        x_pos += running_process_slot.get_width() + GAP
        memory_text_position = (
            x_pos, y_pos + ((running_process_slot.get_height() - memory_text.get_height()) / 2))
        white_inside.blit(memory_text, memory_text_position)
        # Combine
        background.blit(white_inside, (BORDER_WIDTH, BORDER_WIDTH))
        return background

    def pygame_create_blocked_processes_surface(self) -> pygame.Surface:
        '''Creates the surface for the blocked processes'''
        # Set constants
        GAP = 4
        INSET = 5
        BORDER_WIDTH = 2
        FONT_SIZE = 40
        # Create text
        font = pygame.font.Font(None, FONT_SIZE)
        title = font.render('Blocked Processes', True, 'Black')
        title_height = title.get_height()
        title_width = title.get_width()
        # Calculate dimensions
        number_finished_processes = len(self.blocked_processes)
        number_of_gaps = number_finished_processes - 1
        if number_of_gaps < 0:
            number_of_gaps = 0
        width = BORDER_WIDTH + INSET + \
            (number_finished_processes * Process.PYGAME_SURFACE_WIDTH) + \
            (GAP * number_of_gaps) + INSET + BORDER_WIDTH
        minimum_width = BORDER_WIDTH + INSET + title_width + INSET + BORDER_WIDTH
        if width < minimum_width:
            width = minimum_width
        height = BORDER_WIDTH + INSET + title_height + GAP + \
            Process.PYGAME_SURFACE_HEIGHT + INSET + BORDER_WIDTH
        # Create background
        background = pygame.Surface((width, height))
        background.fill('Black')
        # Create white inside
        white_inside_dimensions = (
            width - (BORDER_WIDTH * 2), height - (BORDER_WIDTH * 2))
        white_inside = pygame.Surface(white_inside_dimensions)
        white_inside.fill('White')
        # Add contents
        x_pos = INSET
        y_pos = INSET
        title_position = (
            (white_inside_dimensions[0] - title_width) / 2, y_pos)
        white_inside.blit(title, title_position)
        y_pos += title_height + GAP
        for process in self.blocked_processes:
            process: Process
            white_inside.blit(
                process.pygame_process_surface.surface, (x_pos, y_pos))
            x_pos += Process.PYGAME_SURFACE_WIDTH + GAP
        # Combine
        background.blit(white_inside, (BORDER_WIDTH, BORDER_WIDTH))
        return background

    def pygame_create_finished_processes_surface(self) -> pygame.Surface:
        '''Creates the surface for the finished processes'''
        # Set constants
        GAP = 4
        INSET = 5
        BORDER_WIDTH = 2
        FONT_SIZE = 40
        # Create text
        font = pygame.font.Font(None, FONT_SIZE)
        title = font.render('Finished Processes', True, 'Black')
        title_height = title.get_height()
        title_width = title.get_width()
        # Calculate dimensions
        number_finished_processes = len(self.finished_processes)
        number_of_gaps = number_finished_processes - 1
        if number_of_gaps < 0:
            number_of_gaps = 0
        width = BORDER_WIDTH + INSET + \
            (number_finished_processes * Process.PYGAME_SURFACE_WIDTH) + \
            (GAP * number_of_gaps) + INSET + BORDER_WIDTH
        minimum_width = BORDER_WIDTH + INSET + title_width + INSET + BORDER_WIDTH
        if width < minimum_width:
            width = minimum_width
        height = BORDER_WIDTH + INSET + title_height + GAP + \
            Process.PYGAME_SURFACE_HEIGHT + INSET + BORDER_WIDTH
        # Create background
        background = pygame.Surface((width, height))
        background.fill('Black')
        # Create white inside
        white_inside_dimensions = (
            width - (BORDER_WIDTH * 2), height - (BORDER_WIDTH * 2))
        white_inside = pygame.Surface(white_inside_dimensions)
        white_inside.fill('White')
        # Add contents
        x_pos = INSET
        y_pos = INSET
        title_position = (
            (white_inside_dimensions[0] - title_width) / 2, y_pos)
        white_inside.blit(title, title_position)
        y_pos += title_height + GAP
        for process in self.finished_processes:
            process: Process
            white_inside.blit(
                process.pygame_process_surface.surface, (x_pos, y_pos))
            x_pos += Process.PYGAME_SURFACE_WIDTH + GAP
        # Combine
        background.blit(white_inside, (BORDER_WIDTH, BORDER_WIDTH))
        return background

    async def run(self):
        '''The run cycle of the os process management'''
        screen = pygame.display.set_mode((1500, 900))
        clock = pygame.time.Clock()
        pygame.display.set_caption('Process Scheduler Simulator')
        # Manual exit of the loop via x on graphics
        running = True
        # Loops until there are no unfinished processes left
        while self.unfinished_processes and running:
            # Reset screen
            screen.fill('white')

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # Checks to see if any processes need to be moved
            self.check_running_process()
            self.check_blocked_processes()

            # Generate graphics
            # Add ready queue
            y_pos = 5
            x_pos = 5
            ready_queue_surface = self.pygame_create_ready_queue_surface()
            screen.blit(ready_queue_surface, (x_pos, y_pos))
            # Add CPU surface
            x_pos = 20
            y_pos += ready_queue_surface.get_height() + 8
            cpu_surface = self.pygame_create_cpu_surface()
            screen.blit(cpu_surface, (20, y_pos))
            # Add blocked processes
            x_pos += cpu_surface.get_width() + 40
            blocked_processes_surface = self.pygame_create_blocked_processes_surface()
            centring_adjustment = (cpu_surface.get_height(
            ) - blocked_processes_surface.get_height()) / 2
            screen.blit(blocked_processes_surface,
                        (x_pos, y_pos + centring_adjustment))
            # Add finished_processess
            x_pos = 5
            y_pos += cpu_surface.get_height() + 8
            finished_processes_surface = self.pygame_create_finished_processes_surface()
            screen.blit(finished_processes_surface, (x_pos, y_pos))
            y_pos += finished_processes_surface.get_height() + 8

            # Render pygame stuff
            pygame.display.update()
            clock.tick(60)  # Limits fps to 5

            # Wait
            await asyncio.sleep(0.1)
        print('All processes complete!')
        for process in self.finished_processes:
            process: Process
            print(
                f'{process}: {process.cpu_time_recieved}/{process.time_to_complete}')

        # Destroy the pygame window
        pygame.quit()

    def process_priority_lower_than_queued_processes(self, process: Process):
        if process.priority == ProcessPriority.HIGH:
            return False
        elif process.priority == ProcessPriority.IO:
            if self.ready_queue_HIGH_priority:
                return True
            else:
                return False
        elif process.priority == ProcessPriority.LOW:
            if self.ready_queue_IO_priority or self.ready_queue_HIGH_priority:
                return True
            else:
                return False

    @property
    def unfinished_processes(self) -> bool:
        '''True if there are unfinished processes, else is false. Unfinished processes are processes that are not in the `self.finished_processes` collection'''
        if self.new_process_queue:
            return True
        for list_of_processes in self.ready_queue.values():
            if list_of_processes:
                return True
        if self.running_process:
            return True
        if self.blocked_processes:
            return True
        return False

    @property
    def number_ready_processes(self) -> int:
        number_of_ready_processes = 0
        number_of_ready_processes += len(
            self.ready_queue_HIGH_priority)
        number_of_ready_processes += len(
            self.ready_queue_IO_priority)
        number_of_ready_processes += len(
            self.ready_queue_LOW_priority)
        return number_of_ready_processes

    @property
    def round_robin_timing(self) -> timedelta:
        '''The cpu time each process will get when using round robin scheduling'''
        return self.__round_robin_timing

    @property
    def ready_queue_HIGH_priority(self) -> list[Process]:
        return self.ready_queue[ProcessPriority.HIGH.name]

    def ready_queue_HIGH_priority_pop(self, index: int) -> Process:
        return self.ready_queue[ProcessPriority.HIGH.name].pop(index)

    @property
    def ready_queue_IO_priority(self) -> list[Process]:
        return self.ready_queue[ProcessPriority.IO.name]

    def ready_queue_IO_priority_pop(self, index: int) -> Process:
        return self.ready_queue[ProcessPriority.IO.name].pop(index)

    @property
    def ready_queue_LOW_priority(self) -> list[Process]:
        return self.ready_queue[ProcessPriority.LOW.name]

    def ready_queue_LOW_priority_pop(self, index: int) -> Process:
        return self.ready_queue[ProcessPriority.LOW.name].pop(index)
