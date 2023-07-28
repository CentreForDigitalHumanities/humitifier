from dataclasses import dataclass

@dataclass
class Memory:
    total_mb: int
    used_mb: int
    free_mb: int
    swap_total_mb: int
    swap_used_mb: int
    swap_free_mb: int


    @classmethod
    @property
    def alias(cls) -> str:
        return "memory"

    @classmethod
    def from_stdout(cls, output: list[str]) -> "Memory":
        for line in output:
            match line.strip().partition(":"):
                case "Mem", _, value:
                    mem = [int(v) for v in value.split()]
                case "Swap", _, value:
                    swap = [int(v) for v in value.split()]
        return cls(
            total_mb=mem[0],
            used_mb=mem[1],
            free_mb=mem[2],
            swap_total_mb=swap[0],
            swap_used_mb=swap[1],
            swap_free_mb=swap[2],
        )

    @staticmethod
    def ssh_command(_) -> str:
        return "free -m"