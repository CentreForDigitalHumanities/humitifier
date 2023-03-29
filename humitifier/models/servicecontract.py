import toml
from pydantic import BaseModel
from datetime import date
from .person import Person


class ServiceContract(BaseModel):
    """
    A service contract associated to a server
    """

    entity: str  # The entity that the contract is with. Example: "Hogwarts School of Witchcraft and Wizardry"
    owner: Person  # The owner of the contract. Example: Person(name="Bartolomew Bagshot", email="b.bagshot@hogwarts.co.uk")
    start_date: date  # The date on which the contract was created. Example: date(2022, 12, 31)
    end_date: date  # The expiry date of the contract. Example: date(2022, 12, 31)
    purpose: str  # The purpose of the contract. Example: "webapp"
    people: list[Person]  # A list of people associated to the server. Example: [Person(...), Person(...)]

    @classmethod
    def from_toml(cls, toml_data: dict) -> "ServiceContract":
        override = {
            "owner": Person.from_contract(toml_data["contract"]["owner"]),
            "people": [Person.from_contract(person) for person in toml_data["people"]],
        }
        if isinstance(toml_data["contract"]["start_date"], str):
            override["start_date"] = date.fromisoformat(toml_data["contract"]["start_date"])
        if isinstance(toml_data["contract"]["end_date"], str):
            override["end_date"] = date.fromisoformat(toml_data["contract"]["end_date"])
        create_args = {**toml_data["contract"], **override}
        return cls(**create_args)
