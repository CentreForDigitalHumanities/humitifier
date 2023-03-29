from pydantic import BaseModel


class Package(BaseModel):
    name: str  # The name of the package. Example: "nginx"
    version: str  # The version of the package. Example: "1.21.1-1ubuntu1"

    def __str__(self) -> str:
        return f"{self.name} {self.version}"
