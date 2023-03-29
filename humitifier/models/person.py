from pydantic import BaseModel


class Person(BaseModel):
    """
    A person associated to a server
    """

    name: str  # The name of the person. Example: "Bartolomew Bagshot"
    email: str  # The email address of the person. Example: "bbagshot@hogwarts.co.uk"
    notes: str | None  # Optional notes about the person. Example: "Contact for server maintenance"

    @classmethod
    def from_contract(cls, data: dict) -> "Person":
        return cls(**data)
