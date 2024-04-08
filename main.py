import os
import queue
import shutil
import textwrap
import threading
import time

from dotenv import load_dotenv

from sirji.agents.coder import Coder
from sirji.agents.executor import Executor
from sirji.agents.planner import Planner
from sirji.agents.researcher import Researcher
from sirji.agents.user import User
from sirji.messages.parser import MessageParser
from sirji.tools.logger import coder as cLogger
from sirji.tools.logger import executor as eLogger
from sirji.tools.logger import planner as pLogger
from sirji.tools.logger import researcher as rLogger
from sirji.tools.logger import sirji as sLogger
from sirji.tools.logger import user as uLogger
from sirji.view.chat import (
    disable_chat_send_button,
    enable_chat_send_button,
    run_chat_app,
    send_external_system_message,
)
from sirji.view.screen import get_screen_resolution
from sirji.view.terminal import open_terminal_and_run_command

last_recipient = ""

# Global queue to safely exchange messages between threads
messages_queue = queue.Queue()


def empty_workspace():
    workspace_dir = "workspace"

    # List all files and directories in the workspace directory
    for item in os.listdir(workspace_dir):
        if item == "logs":
            continue  # Skip the code directory

        item_path = os.path.join(workspace_dir, item)

        try:
            # If it's a directory, remove it along with its contents
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            # If it's a file, remove it
            else:
                os.remove(item_path)
        except Exception as e:
            print(f"Error removing {item_path}: {e}")


class Main:
    def __init__(self):
        self.problem_statement = None  # Placeholder
        self.initialize_logs()

        self.coder = Coder()
        self.planner = Planner()
        self.researcher = Researcher("openai_assistant", "openai_assistant")
        self.executor = Executor()
        self.user = User()

    def truncate_logs(self):
        # List of loggers
        loggers = [cLogger, rLogger, pLogger, eLogger, sLogger, uLogger]

        for logger in loggers:
            # Check if logger is present
            if logger is not None:
                try:
                    # Check if the file exists at the given location
                    if os.path.exists(logger.filepath):
                        # File exists, so open it in 'w' mode to clear or create it, then immediately close it
                        open(logger.filepath, "w").close()
                    else:
                        # If the file does not exist, handle accordingly (e.g., log this situation or take other actions)
                        print(f"File does not exist at {logger.filepath}.")

                except AttributeError:
                    # Handle the case where the logger doesn't have a 'filepath' attribute
                    print(f"Logger {logger} does not have a 'filepath' attribute.")

                except IOError as e:
                    # Handle other I/O errors, such as permission errors
                    print(
                        f"Failed to open file for logger {logger} at {logger.filepath}: {e}"
                    )

    def initialize_logs(self):
        # Truncate the logs
        self.truncate_logs()

        # Initialize the logs
        cLogger.initialize_logs(
            "Coder: Specializing in generating and modifying code, this agent is skilled in various programming languages and is equipped to handle tasks ranging from quick fixes to developing complex algorithms.\n\n\n"
        )

        rLogger.initialize_logs(
            "Researcher: dives into vast pools of information to find answers, evidence, or data that support the task at hand. Whether it's through browsing the web, accessing databases, or consulting academic journals, this agent is adept at gathering and synthesizing relevant information to aid in problem-solving.\n\n\n"
        )

        pLogger.initialize_logs(
            "Planner: planner is tasked with orchestrating the overall strategy for solving user queries. Assesses the problem statement and determines the most effective sequence of actions, delegating tasks to other agents and tools as necessary. This agent ensures that Sirji's workflow is efficient and goal-oriented.\n\n\n"
        )

        eLogger.initialize_logs(
            "Executor: responsible for running code or scripts in a controlled environment, allowing for executing and testing activities. Executor verifies the correctness and efficacy of solutions before they are finalized and implements automated tasks as defined by the Planner.\n\n\n"
        )

        sLogger.initialize_logs(
            "Sirji: Sirji will automatically create a plan to solve the problem statement, prioritize it, organize research, write code, execute it, and fix issues.\n\n\n"
        )

        uLogger.initialize_logs(
            "User: The user is the person who interacts with Sirji. The user can ask questions, provide problem statements, and receive solutions from Sirji.\n\n\n"
        )

    def open_views(self):
        screen_width, screen_height = get_screen_resolution()
        margin = 5  # Margin size in pixels
        window_width = (screen_width - 3 * margin) // 2
        window_height = (screen_height - 22 - 4 * margin) // 3

        command_title_pairs = [
            (f"watch -n 1 'cat {pLogger.filepath}'", "Plan Progress"),
            (f"tail -f {rLogger.filepath}", "Research Agent"),
            (f"tail -f {cLogger.filepath}", "Coding Agent"),
            (f"tail -f {eLogger.filepath}", "Execution Agent"),
        ]

        current_directory = os.getcwd()

        # Prepend `cd {current_directory} &&` to each command to ensure it runs in the desired directory
        command_title_pairs = [
            (f"cd {current_directory} && {command}", title)
            for command, title in command_title_pairs
        ]

        for i, (command, title) in enumerate(command_title_pairs):
            open_terminal_and_run_command(
                command, title, i, window_width, window_height
            )

    def _parse_response(self, response_str):
        """
        Parses the response string to a dictionary.
        """
        print(response_str)
        response = MessageParser.parse(response_str)
        return response

    def handle_response(self, message):
        """
        Recursively passes the response object among different objects.
        """

        global last_recipient  # Declare that we intend to use the global variable

        try:
            response = self._parse_response(message)
            recipient = response.get("TO").strip()
            sender = response.get("FROM").strip()
            action = response.get("ACTION").strip()
        except Exception:
            recipient = last_recipient
            message = textwrap.dedent(f"""
              ```
              FROM: User
              TO: {recipient}
              ACTION: acknowledge
              DETAILS: Sure.
              ```
              """)
            response = self._parse_response(message)
            recipient = response.get("TO").strip()
            sender = response.get("FROM").strip()
            action = response.get("ACTION").strip()

        send_external_system_message(
            f"Forwarding message from {sender} to {recipient} for action: {action}"
        )

        response_message = ""

        if action == "question" or action == "inform":
            details = response.get("DETAILS")
            send_external_system_message(f"Question: {details}")
            enable_chat_send_button()

            user_input = self.wait_for_user_input()

            ans_message = self.user.generate_answer_message(user_input, "Coder")

            disable_chat_send_button()
            self.handle_response(ans_message)
        elif action == "solution-complete":
            details = response.get("DETAILS")
            send_external_system_message(f" Solution complete: {details}")
            enable_chat_send_button()

            user_input = self.wait_for_user_input()

            ans_message = self.user.generate_feedback_message(user_input, "Coder")
            disable_chat_send_button()
            self.handle_response(ans_message)

        # Pass the response to the appropriate object and update the response object.
        if recipient == "Coder":
            response_message = self.coder.message(message)
        elif recipient == "Planner":
            response_message = self.planner.message(message)
        elif recipient == "Executor":
            response_message = self.executor.message(message)
        elif recipient == "Researcher":
            response_message = self.researcher.message(message)
        elif recipient == "User":
            response_message = self.user.message(message)
            # Optionally, insert a return or break statement if 'UR' is a terminal condition.
        else:
            raise ValueError(f"Unknown recipient type: {recipient}")

        last_recipient = recipient

        self.handle_response(response_message)

    def start(self):
        self.open_views()

        send_external_system_message(
            "Hello! Please provide the problem you need me to solve."
        )

        while True:
            # Wait for a new message to become available
            self.problem_statement = messages_queue.get()
            print(self.problem_statement)
            break

        disable_chat_send_button()

        ps_message = self.user.generate_problem_statement_message(
            self.problem_statement, "Coder"
        )

        response_message = self.coder.message(ps_message)

        self.handle_response(response_message)

    def wait_for_user_input(self):
        user_input = ""
        while True:
            # Wait for a new message to become available
            time.sleep(1)
            user_input = messages_queue.get()
            break

        print(f"User input: {user_input}")
        return user_input


def perform_non_gui_tasks():
    Main().start()


if __name__ == "__main__":
    empty_workspace()
    load_dotenv()

    background_thread = threading.Thread(target=perform_non_gui_tasks)
    background_thread.start()

    # Pass the messages_queue to the ChatApp instance
    run_chat_app(messages_queue)
