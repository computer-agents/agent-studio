import time

from playground.desktop_env.computer.env import ComputerEnv

computer = ComputerEnv()

print("Type out a string of characters, computer with display only")
time.sleep(3)
computer.keyboard.write("Hello hi")

print("Get the selected text, computer with display only")
time.sleep(1)
text = computer.os.get_selected_text()
print("Selected text:", text)

print("Get screenshot, plot, and move mouse, computer with display only")
print("Moving mouse to (500, 800), please wait...")
computer.verbose = True
computer.mouse.move(
    x=500, y=800
)  # pixel coordinates (e.g., x=1920, y=1080), lefttop is (0, 0)

computer.run("shell", "code --list-extensions")

for chunk in computer.run("python", "print('Hello World')"):
    print(chunk)
