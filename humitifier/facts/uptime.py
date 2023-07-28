from datetime import timedelta

class Uptime(timedelta):

    @classmethod
    @property
    def alias(cls) -> str:
        return "uptime"

    @classmethod
    def from_stdout(cls, output: list[str]) -> "Uptime":
        line = output[0].replace("up ", "")
        args = {}
        for part in line.split(", "):
            value, _, name = part.strip().partition(" ")
            args[name] = int(value)
        fixed = {k + "s" if not k.endswith("s") else k: v for k, v in args.items()}
        if "years" in fixed:
            fixed["days"] = fixed.get("days", 0) + fixed.pop("years") * 365
        return cls(**fixed)

    @staticmethod
    def ssh_command(_) -> str:
        return "uptime -p"