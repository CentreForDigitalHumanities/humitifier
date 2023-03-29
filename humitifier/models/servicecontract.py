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
