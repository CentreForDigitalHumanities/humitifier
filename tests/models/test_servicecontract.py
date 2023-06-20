import toml
from humitifier.models.servicecontract import ServiceContract

example_toml = """
[contract]
fqdn = "db-01.hogwarts.co.uk"
entity = "Department of Magical Creatures"
start_date = "2022-02-01"
end_date = "2023-02-28"
purpose = "db-server"
owner = { name = "Rubeus Hagrid", email = "r.hagrid@hogwarts.co.uk"}

[[people]]
name = "Bathilda Bagshot"
email = "b.bagshot@hogwarts.co.uk"
notes = "Contact for dev support"

[[people]]
name = "Severus Snape"
email = "s.snape@hogwarts.co.uk"
"""


def test_servicecontract_loads_correctly():
    data = toml.loads(example_toml)
    contract = ServiceContract.from_toml(data)
    assert contract.entity == "Department of Magical Creatures"
    assert contract.owner.name == "Rubeus Hagrid"
    assert len(contract.people) == 2
