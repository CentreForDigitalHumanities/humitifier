from enum import Enum, auto
from jinja2 import Template


BASE = Template("""
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="static/out.css" rel="stylesheet">
    <script src="https://unpkg.com/htmx.org@1.8.6"
        integrity="sha384-Bj8qm/6B+71E6FQSySofJOUjA/gq330vEqjFx9LakWybUySyI1IQHwPtbTU7bNwx"
        crossorigin="anonymous"></script>
    <title>Humitifier</title>

</head>

<body>
    {{ content|safe }}
</body>

</html>
""")


class Wrapper(Enum):
    Base = auto()
    HxOobSwap = auto()

    def render(self, html_content: str, **kwargs) -> str:
        match self:
            case Wrapper.Base:
                return BASE.render(content=html_content)
            case Wrapper.HxOobSwap:
                if "target" not in kwargs:
                    raise ValueError("Wrapper.HxOobSwap requires 'target' kwarg")
                return Template(
                    """<div hx-swap-oob="{{target}}">{{content|safe}}</div>"""
                    ).render(target=kwargs["target"], content=html_content)

