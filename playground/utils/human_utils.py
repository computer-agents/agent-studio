def confirm_action(func):
    def wrapper(*args, **kwargs):
        user_input = input("Confirm action (y/n): ").strip().lower()
        if user_input == "y":
            return func(*args, **kwargs)
        else:
            return False

    return wrapper
