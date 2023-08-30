from memory import Memory
from datetime import timedelta, datetime
from enums import ProcessPriority, ProcessStatus, PreemptReason, priority_colors
from typing import Union, TypedDict
import pygame


class ProcessSurface:
    FONT_HEIGHT = 25
    PROGRESS_BAR_HEIGHT = 25
    PROGRESS_BAR_INSET = 5

    def __init__(self, width: int, height: int, process_name: str, progress: float, memory_usage: Memory, priority: ProcessPriority) -> None:
        self.size = (width, height)

        # Create black outline box
        self.surface = pygame.Surface(self.size)
        self.surface.fill('Black')
        self.white_inside_size = (self.size[0] - 2, self.size[1] - 2)
        self.white_inside = pygame.Surface(self.white_inside_size)
        self.white_inside.fill('White')
        self.surface.blit(self.white_inside, (1, 1))

        # Create font
        self.font = pygame.font.Font(None, ProcessSurface.FONT_HEIGHT)
        # Add process name
        self.process_name = self.font.render(process_name, True, 'Black')
        self.process_name_position = (
            (self.white_inside_size[0] - self.process_name.get_width()) / 2, 60)
        self.surface.blit(self.process_name, self.process_name_position)
        # Add memory usage
        self.memory_usage = self.font.render(
            memory_usage.__repr__(), True, 'Black')
        self.memory_usage_position = (
            (self.white_inside_size[0] - self.memory_usage.get_width()) / 2, 140)
        self.surface.blit(self.memory_usage, self.memory_usage_position)
        # Add priority
        self.priority_text_color = priority_colors[priority]
        self.priority_text = self.font.render(
            priority.name, True, self.priority_text_color)
        self.priority_text_position = (
            (self.white_inside_size[0] - self.priority_text.get_width()) / 2, 85)
        self.surface.blit(self.priority_text, self.priority_text_position)

        # Create progess bar
        self.progress_bar_width = self.size[0] - \
            (ProcessSurface.PROGRESS_BAR_INSET * 2)
        self.progess_bar = pygame.Surface(
            (self.progress_bar_width, ProcessSurface.PROGRESS_BAR_HEIGHT))
        self.progess_bar.fill('Black')
        # Create box
        self.white_inside_progess_bar_width = self.progress_bar_width - 2
        self.white_inside_progess_bar = pygame.Surface(
            (self.white_inside_progess_bar_width, ProcessSurface.PROGRESS_BAR_HEIGHT-2))
        self.white_inside_progess_bar.fill('White')
        # Add green progress indicator
        self.progress_max_width = self.white_inside_progess_bar_width - 2
        self.progress_height = ProcessSurface.PROGRESS_BAR_HEIGHT - 4
        self.progess_width = self.progress_max_width * progress
        if progress > 1:
            self.progess_width = self.progress_max_width
        self.progress = pygame.Surface(
            (self.progess_width, self.progress_height))
        self.progress.fill('Green')
        self.white_inside_progess_bar.blit(self.progress, (1, 1))
        self.progess_bar.blit(self.white_inside_progess_bar, (1, 1))
        # Add progress bar to surface
        self.surface.blit(self.progess_bar,
                          (ProcessSurface.PROGRESS_BAR_INSET, 110))


class Preemption:
    '''Preemption objects are added to a process to tell the os why and when the process has recieved all cpu time given'''

    def __init__(self, reason: PreemptReason, time_of_preemption: timedelta, blocked_function: callable):
        self.__preempt_reason = reason
        self.__time_of_preemption = time_of_preemption
        # The function that determines how long the process has to wait until it is no longer blocked
        self.__blocked_generator = blocked_function()
        self.__is_complete: bool = False

    @property
    def preempt_reason(self) -> PreemptReason:
        return self.__preempt_reason

    @property
    def time_of_preemption(self) -> timedelta:
        return self.__time_of_preemption

    @property
    def still_blocked(self) -> bool:
        '''Runs the generator provided that tells the os whether the process can be unblocked. `True` means the process must stay blocked.'''
        return next(self.__blocked_generator)

    @property
    def is_complete(self) -> bool:
        '''Shows if the preemption has occured'''
        return self.__is_complete

    def complete(self) -> None:
        self.__is_complete = True

    def __repr__(self) -> str:
        return f'{self.preempt_reason} at {self.time_of_preemption}'


def default_preemption_blocked_function() -> bool:
    '''Returns `True`'''
    return True


class BlockingPreemptionWithPosition(TypedDict):
    index: int
    preemption: Preemption


class Process:
    counter = 1
    PYGAME_SURFACE_WIDTH = 135
    PYGAME_SURFACE_HEIGHT = 180

    def __init__(self, time_to_complete: timedelta, memory_required: Memory, priority: ProcessPriority):
        self.__time_to_complete: timedelta = time_to_complete
        self.__memory_required: Memory = memory_required
        self.__status = ProcessStatus.NEW
        self.__priority: ProcessPriority = priority
        self.__cpu_time_recieved: timedelta = timedelta(seconds=0)
        self.__cpu_time_over: Union(bool, PreemptReason) = False
        self.__preemptions = []
        self.__time_at_last_time_check: datetime = None
        self.__running = False
        self.__identifier = 'Process' + str(Process.counter)
        Process.counter += 1
        self.pygame_process_surface = ProcessSurface(
            Process.PYGAME_SURFACE_WIDTH, Process.PYGAME_SURFACE_HEIGHT, self.__repr__(), 0, self.__memory_required, self.__priority)

    def add_preemption(self, reason: PreemptReason, time_till_preemption: timedelta = None, blocked_function: callable = None) -> None:
        '''Adds a `Preemption` to the `self.__preemptions` list of preemptions'''
        # Creates a time of preemption variable in local scope
        time_of_preemption = None
        # Creates a default argument for the preemption blocked_function argument
        blocked_function_arguement: function = default_preemption_blocked_function
        if reason == PreemptReason.COMPLETION:
            # Process should only be preempted when process has finshed running
            time_of_preemption = self.time_to_complete
        elif reason == PreemptReason.ROUND_ROBIN or reason == PreemptReason.BLOCKED:
            # Process should be preempted after a given period of time, or when the process completes, whichever comes first
            prospective_time_to_complete = self.cpu_time_recieved + time_till_preemption
            if self.time_to_complete < prospective_time_to_complete:
                time_of_preemption = self.time_to_complete
            else:
                time_of_preemption = prospective_time_to_complete
        if reason == PreemptReason.BLOCKED:
            # Correct blocked function set
            blocked_function_arguement = blocked_function
        # Preemption added to list of preemptions
        self.__preemptions.append(Preemption(
            reason, time_of_preemption, blocked_function_arguement))

    def remove_preemption(self, index: int):
        '''Removes preemption from `self.__premptions` at index given.'''
        self.__preemptions.pop(index)
        self.__cpu_time_over = False

    def __repr__(self):
        return self.__identifier

    @property
    def identifier(self) -> str:
        return self.__identifier

    @property
    def blocking_preemptions(self) -> list[BlockingPreemptionWithPosition]:
        '''Returns all preemptions attached to process with preemption reason `PreemptReason.BLOCKED` in dicts in format `dict['index': int, 'preemption': Preemption]`'''
        blocking_preemptions_to_return: list[BlockingPreemptionWithPosition] = [
        ]
        for index, preemption in enumerate(self.preemptions):
            if preemption.preempt_reason == PreemptReason.BLOCKED:
                blocking_preemptions_to_return.append(
                    {'index': index, 'preemption': preemption})
        return blocking_preemptions_to_return

    @property
    def running(self) -> bool:
        return self.__running

    @running.setter
    def running(self, value: bool) -> None:
        '''Takes a `bool`. If true, begins to run the process, else stops running it'''
        if value:
            self.__time_at_last_time_check = datetime.now()
            self.__running = True
        else:
            self.__time_at_last_time_check = None
            self.__running = False

    def calculate_cpu_time_recieved(self):
        time_recieved = datetime.now() - self.__time_at_last_time_check
        self.increment_cpu_time_recieved(time_recieved)
        self.__time_at_last_time_check = datetime.now()
        self.pygame_process_surface = ProcessSurface(
            Process.PYGAME_SURFACE_WIDTH, Process.PYGAME_SURFACE_HEIGHT, self.__repr__(), self.cpu_time_recieved/self.time_to_complete, self.memory_required, self.priority)

    @property
    def preemptions(self) -> list[Preemption]:
        return self.__preemptions

    @property
    def time_to_complete(self) -> timedelta:
        return self.__time_to_complete

    '''@time_to_complete.setter
    def time_to_complete(self, new_time_to_complete):
        self.__time_to_complete = new_time_to_complete'''

    @property
    def status(self) -> ProcessStatus:
        return self.__status

    @status.setter
    def status(self, new_status: ProcessStatus) -> None:
        '''Changes status to different process status, and changes `self.running` to reflect change in status.'''
        self.__status = new_status
        if new_status == ProcessStatus.RUNNING:
            self.running = True
        else:
            self.running = False

    @property
    def memory_required(self) -> Memory:
        return self.__memory_required

    @property
    def priority(self) -> ProcessPriority:
        return self.__priority

    @property
    def cpu_time_recieved(self):
        return self.__cpu_time_recieved

    def increment_cpu_time_recieved(self, increment: timedelta) -> None:
        '''Increments `self.__cpu_time_complete` and checks if process needs to be blocked, finsished, or otherwise removed from having cpu time.'''
        self.__cpu_time_recieved += increment
        # Checks if any preemptions are triggered
        for preemption in self.preemptions:
            print(preemption)
            if self.cpu_time_recieved >= preemption.time_of_preemption:
                preemption.complete()
                self.__cpu_time_over = preemption.preempt_reason
                return

    @property
    def cpu_time_over(self) -> bool:
        '''If `self.__cpu_time_recieved >= preemption.time_of_preemption` for any preemption attached to the process, then `self.__cpu_time_over` holds the reason for preemption. Otherwise holds False'''
        return self.__cpu_time_over
