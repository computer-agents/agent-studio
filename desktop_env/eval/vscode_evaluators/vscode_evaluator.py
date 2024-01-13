import os

from rich import print


def installed_vscode_extension(extension_name):
    output = os.popen("code --list-extensions").readlines()
    output = [line.strip() for line in output]  # removes \n
    return extension_name in output

def uninstall_vscode_extension(extension_name):
    not installed_vscode_extension(extension_name)


if __name__ == "__main__":
    print('installed_vscode_extension',installed_vscode_extension("ms-python.python"))
    print('uninstall_vscode_extension',uninstall_vscode_extension("ms-python.python"))


