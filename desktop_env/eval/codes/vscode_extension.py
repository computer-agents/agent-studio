import os

from rich import print


def check_vscode_extension(extension_name):
    output = os.popen("code --list-extensions").readlines()
    output = [line.strip() for line in output]  # removes \n
    return extension_name in output


if __name__ == "__main__":
    print(check_vscode_extension("ms-python.python"))
