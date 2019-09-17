import os
import tempfile

PROMPT = "[RADAR PROMPT]"

INTERCEPT_COMMANDS = [
    "exit",
    "cd",
    "radar"
]


def update_prompt():
    global PROMPT
    PROMPT = f"[RADAR] {os.getcwd()} > "


def process_intercepted_command(command):
    if command == 'exit':
        print("$$$  Thanks for joining the Red-team Analysis, Documentation, and Automation Revolution!")
        exit(0)
    elif 'cd' in command:
        directory = ""
        try:
            directory = command.split(' ', 1)[1]
            os.chdir(directory)
            update_prompt()
        except (IndexError, FileNotFoundError):
            print(f"!!!  Invalid directory: '{directory}'")
    else:
        print(f"!!!  Your command was intercepted but wasn't processed: {command}")


def main():
    update_prompt()
    while True:
        user_input = str(input(PROMPT)).strip()
        program = user_input.split(' ', 1)[0]

        # Check if command should be processed differently from a system command
        if any(intcmd in user_input for intcmd in INTERCEPT_COMMANDS):
            process_intercepted_command(user_input)
            continue

        # Else run command through system shell
        # Create temporary file to store command output
        temp_output_file = tempfile.NamedTemporaryFile(suffix='.out', prefix='tmp', delete=False)
        temp_filepath = temp_output_file.name
        temp_output_file.close()  # Release lock on file

        # Run a command and pipe it's output to the file
        process = os.system(f"{user_input} > {temp_filepath}")

        # Grab command output from tempfile and print it out
        with open(temp_filepath, 'r') as temp_output_file:
            contents = temp_output_file.read()
        print(contents, end='')  # Print file as it appears

        os.remove(temp_filepath)  # Delete tempfile


if __name__ == '__main__':
    main()