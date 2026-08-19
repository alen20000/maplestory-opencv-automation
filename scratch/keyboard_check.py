import keyboard

def print_key(event):
    print(event)

keyboard.hook(print_key)
keyboard.wait()


