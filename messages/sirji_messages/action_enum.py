from enum import Enum, auto


class ActionEnum(Enum):
    ACKNOWLEDGE = auto()
    ANSWER = auto()
    EXECUTE_COMMAND = auto()
    CREATE_FILE = auto()
    GENERATE_STEPS = auto()
    PROBLEM_STATEMENT = auto()
    INFER = auto()
    INFORM = auto()
    INSTALL_PACKAGE = auto()
    OUTPUT = auto()
    QUESTION = auto()
    RESPONSE = auto()
    SOLUTION_COMPLETE = auto()
    STEP_COMPLETED = auto()
    STEP_STARTED = auto()
    STEPS = auto()
    TRAIN_USING_SEARCH_TERM = auto()
    TRAIN_USING_URL = auto()
    FEEDBACK = auto()
    TRAINING_OUTPUT = auto()
