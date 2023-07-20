from enum import Enum, auto
from jinja2 import Template

from humitifier.models.person import Person
from humitifier.facts import Package


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


class Atom(Enum):
    String = auto()
    Progress = auto()
    MailToPerson = auto()
    MailToPeopleList = auto()
    InlineListStrings = auto()
    InlineListPackages = auto()
    DaysString = auto()
    MegaBytesString = auto()

    def render(self, properties) -> str:
        match self:
            case Atom.String: 
                return str(properties)
            case Atom.Progress:
                if "description" not in properties or "value" not in properties:
                    raise ValueError("Progress atom requires 'description' and 'value' properties")
                return Template("""
                    <div class="progress" data-label="{{props.description}}">
                        <span class="value" style="width:{{props.value}}%;"></span>
                    </div>""").render(props=properties)
            case Atom.MailToPerson:
                if not isinstance(properties, Person):
                    raise ValueError("MailToPerson atom requires a Person object")
                return Template("""
                    <a href="mailto:{{ person.email }}">{{ person }}</a>
                    {% if person.notes %}
                    <abbr title="{{ person.notes }}">🛈</abbr>
                    {% endif %}
                    """).render(person=properties)
            case Atom.MailToPeopleList:
                if not isinstance(properties, list) or not all(isinstance(p, Person) for p in properties):
                    raise ValueError("MailToPerson atom requires a list of Person objects")
                return Template("""<ul>
                    {% for person_html in people %}
                    <li>{{ person_html|safe }}</li>
                    {% endfor %}
                    </ul>"""
                ).render(people=[Atom.MailToPerson.render(p) for p in properties])
            case Atom.InlineListStrings:
                if not isinstance(properties, list) or not all(isinstance(s, str) for s in properties):
                    raise ValueError("InlineList atom requires a list")
                return Template("""
                    <ul class=inline-list>
                        {% for item in items %}
                        <li>{{ item }}</li>
                        {% endfor %}
                    </ul>""").render(items=properties)
            case Atom.InlineListPackages:
                if not isinstance(properties, list) or not all(isinstance(s, Package) for s in properties):
                    raise ValueError("InlineList atom requires a list of Package objects")
                return Atom.InlineListStrings.render([str(p) for p in properties])
            case Atom.DaysString:
                if not isinstance(properties, int):
                    raise ValueError("DaysString atom requires an int")
                return f"{properties} days"
            case Atom.MegaBytesString:
                if not isinstance(properties, int):
                    raise ValueError("DaysString atom requires an int")
                return f"{properties} MB"