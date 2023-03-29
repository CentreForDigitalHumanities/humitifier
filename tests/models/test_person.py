from humitifier.models.person import Person

example_data = {"name": "Bartolomew Bagshot", "email": "b.bagshot@hogwarts.co.uk"}


def test_person_loads_correctly():
    person = Person.from_contract(example_data)
    assert person.name == "Bartolomew Bagshot"
    assert person.email == "b.bagshot@hogwarts.co.uk"
