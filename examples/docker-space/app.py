from unique_interface import Interface


def predict(name):
    return f"Hello, {name}!"


Interface(predict, title="My Unique demo").launch(space=True)
