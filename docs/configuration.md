# Running Humitifier

Humitifier is highly configurable through custom code.
To understand what is going on, below is an outline of setting up your own humitifier environment on different levels.

## Level 0: Just builtin facts and properties

Humitifier comes with a number of builtin facts and properties that you can use.
There is one key difference between `facts` and `properties`:

- `facts` are data objects generated directly from running a command over ssh on a host
- `properties` are objects that extract information from `facts` and make them viewable

In other words, to access fact-based properties, you **need** to have the fact available.
The avaialble facts can be found in the [source code](../humitifier/facts.py).

An example of such a fact is `HostnameCtl`, which as you may have guessed provides the data from `hostnamectl`.
In this case, we are interested in the operating system of the hiost, so we want to read out that specific property.
Such a property is also built into humitfier, to view all properties for fact-based data, check [the source code](../humitifier/properties/facts.py).
The property is called `Os`.

To include this property into our app configuration, we modify `user_data/__init__.py`:

```python
from humitifier.config import AppConfig
from humitifier.facts import HostnameCtl
from humitifier.properties.facts import Os

config = AppConfig(
    environment="demo",
    hosts=[],
    facts=[HostnameCtl],
    filters=[],
    metadata_properties=[],
    fact_properties=[Os],
    grid_properties=[],
    pssh_config={},
    poll_interval="every 20 minutes"
)
```

With this configuration we make sure that any host will have the `hostnamectl` info and that the details table of each host shows the operating system.
To make the app functional, you must add a host and create the app.

```python
from humitifier.app import create_base_app
from humitifier.models.host import Host
from humitifier.config import AppConfig
from humitifier.facts import HostnameCtl
from humitifier.properties.facts import Os

hosts = [
    Host(fqdn="<YOUR HOST FQDN HERE>", metadata={})
]

config = AppConfig(
    environment="demo",
    hosts=hosts,
    facts=[HostnameCtl],
    filters=[],
    metadata_properties=[],
    fact_properties=[Os],
    grid_properties=[],
    pssh_config={},
    poll_interval="every 20 minutes"
)

app = create_base_app(config)
```

You can now run the app through docker-ccompose.

## Level 1: More properties

So far we have added just the os property, but we might be interested in more properties.
Additionally we might want to immediately see information before clicking on the details button.
This quick info is visible in the grid view, so we can add the properties we care about in `grid_properties`:

```python
...

config = AppConfig(
    grid_properties=[Os],
    ...
)
```

Looking at the available properties, we see some other things that can be extracted from just hostnamectl:

```python
from humitifier.properties.facts import Os, Hostname 

config = AppConfig(
    fact_properties=[Os, Hostname],
    grid_properties=[Os],
    ...
)
```

With this configuration, you see the `Os` property immediately when viewing all hosts and when you click on the details table, ypu see the hostname too.

## Level 2: Metadata properties

Previously when the `Host` was initialized, the `metadata` property was a blank hashtable.
This field is used to provide information about a host that is not directly available on the host.
This can be stuff like when you want to retire a server or who to contact.
Generally this will involve writing custom code to get exactly the values you want, but humitifier comes with [some defaults](../humitifier/properties/metadata.py).
For instance, you might be interested in the department that a host belongs to.
For that, the host must be changed and a property must be added in the config:

```python
...
from humitifier.properties.metadata import Department

hosts = [
    Host(fqdn="<YOUR HOST FQDN HERE>", metadata={"department": "Ministry for Magic"})
]

config = AppConfig(
    meta_properties=[Department],
    ...
)
```

With this setup, the department is visible in the details table of a host.
Take note: there is no difference between fact-based properties and metadata properties, meaning you can add this property to `grid_properties` as well.
You could even add it to `fact_properties` and nothing would break.
The difference between `fact_properties`, `meta_properties`, and `grid_properties` is solely the place and the way in which they get rendered.

## Level 3: Filters

If you want to be able to filter hsots on certain properties, you can add filters to the configuration.
Again, humitifier comes with [builtins](../humitifier/filters.py).
This can be added to the config:

```python
from humitifier.fitlers import DepartmentFilter

config = AppConfig(
    filters=[DepartmentFilter],
    ...
)
```

Now the app will render with a department filter allowing you to dynamically filter your hosts.

## Level 4: Rules

TODO

## Level 5: Customization

Up until now, only the builtins of humitifier have been used.
But nothing stops you from implementing additional facts, properties, filters, and rules for your implementation.
Humitifier operates on an interface-like concept and as long as you implement the required properties and methods, you can add your own customizations.
These protocols are specified in the [source code](../humitifier/protocols.py)

For example, the protocol for a property demands 4 things:

- a `kv_label` that describes how the value will be identified in the details table
- a `slug` classmethod returning a unique string
- a `from_host_state` classmethod returning an instance of the property
- a `kv_value_html` property returning html of the property to be rendered in the details table

An example imlpementation might be:

```python
@dataclass
class Color(IProperty):
    r: int
    g: int
    b: int
    kv_label: str = "Color of server"

    @classmethod
    def slug(cls) -> str:
        return "color"

    @classmethod
    def from_host_state(cls, host_state: HostState) -> "Color":
        return cls(r=host_state.host.metadata["color"]["r"], g=host_state.host.metadata["color"]["g"], b=host_state.host.metadata["color"]["b"])

    def render_kv_value(self) -> str:
        return f"Red: {self.r}, Green: {self.g}, Blue: {self.r}"
    
```

The `host_state` has access to both the facts and the metadata allowing you to build complex properties.

The same approach can be applied to filters, facts, and rules.
Refer to the source code to see example implementations of these objects.
There is nothing stopping you from using the same class to implement multiple interfaces.
You could for instance extend the `Color` property with the requirements for `IFact` and stick into the facts configuration without issue.
