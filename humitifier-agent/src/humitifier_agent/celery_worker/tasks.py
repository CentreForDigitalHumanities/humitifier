from .config import app


@app.task(name="agent.test")
def test():
    return add.delay(1, 2)


@app.task(name="agent.add")
def add(x, y):
    return x + y
