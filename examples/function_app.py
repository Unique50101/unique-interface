from unique_interface import Interface, Slider


def greet(name, count):
    return "\n".join([f"Hello, {name}!"] * int(count))


if __name__ == "__main__":
    Interface(greet, ["text", Slider(1, 5, label="Repeats")], "text",
              title="Greeting demo").launch(share=True)
