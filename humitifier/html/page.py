from .protocols import HtmlComponent
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
    <section id="host-grid-page">
        <header class="main-header">
            <img src="static/img/uu-rgb-black.png" alt="logo" class="logo">
            <main>
                <h1>Monitor Servers, <br /><em>Mess up less</em></h1>
            </main>
            <aside></aside>
        </header>          
        <article id="hx-modal"></article>
        {% for component in components %}
        {{ component.render()|safe }}
        {% endfor %}
    </section>
    
</body>

</html>
""")

class Page(list[HtmlComponent]):
    def render(self) -> str:
        return BASE.render(components=self)