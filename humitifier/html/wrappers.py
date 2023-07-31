from dataclasses import dataclass
from jinja2 import Template
from .protocols import HtmlComponent


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
                
@dataclass
class Base:
    content: HtmlComponent
    template = BASE

    def __str__(self) -> str:
        return self.template.render(content=self.content)

    
@dataclass
class HxSwap:
    html: HtmlComponent
    target: str
    template = Template(
        """<div hx-swap-oob="{{target}}">{{html|safe}}</div>"""
    )

    def __str__(self) -> str:
        return self.template.render(
            html=self.html, 
            target=self.target
        )