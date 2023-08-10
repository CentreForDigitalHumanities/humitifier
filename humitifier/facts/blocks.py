from dataclasses import dataclass

@dataclass
class Block:
    name: str
    size_mb: int
    used_mb: int
    available_mb: int
    use_percent: int
    mount: str

    @classmethod
    def from_line(cls, output_line: str) -> list["Block"]:
        name, size, used, available, use_percent, mount = output_line.strip().split()
        return cls(
            name=name.strip(),
            size_mb=int(size),
            used_mb=int(used),
            available_mb=int(available),
            use_percent=int(use_percent.rstrip("%")),
            mount=mount.strip(),
        )


class Blocks(list[Block]):

    
    @classmethod
    @property
    def alias(cls) -> str:
        return "blocks"

    @classmethod
    def from_stdout(cls, output: list[str]) -> "Blocks":
        blocks = [Block.from_line(line) for line in output[1:]]
        return cls(blocks)
    
    @staticmethod
    def ssh_command(_) -> str:
        return "df | egrep '^/'"