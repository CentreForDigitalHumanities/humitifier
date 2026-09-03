import dataclasses
import subprocess
import sys


class NetworkError(Exception):
    pass


@dataclasses.dataclass
class PingStats:
    transmitted: int
    received: int
    packet_loss: int
    time: int
    avg_time: float


class NetworkExecutor:

    def ping(self, target: str, count: int = 4, interval: float = 1.0) -> PingStats:

        command = ["ping"]

        if sys.platform.lower() == "win32":
            # Windows only supports count, using -n
            command.append("-n")
            command.append(str(count))
        else:
            # Linux and macOS support count and interval, using -c and -i
            command.append("-c")
            command.append(str(count))
            command.append("-i")
            command.append(str(interval))

        command.append(target)

        # logger.debug(f"Pinging {target} with command: {command}")

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise NetworkError(f"Ping failed: {result.stderr}")

        return self._parse_ping_output(result.stdout)

    def _parse_ping_output(self, output: str) -> PingStats:
        lines = output.splitlines()
        transmitted, received, packet_loss, time, ping_cumulative_time = 0, 0, 0, 0, 0
        # 1 packets transmitted, 1 received, 0% packet loss, time 0ms
        for line in lines:
            if "bytes from" in line:
                segments = line.split(" ")
                for segment in segments:
                    if "time" in segment:
                        ping_cumulative_time += float(
                            segment.strip().split("=", maxsplit=1)[1]
                        )
            if "packets transmitted" in line:
                segments = line.split(",")
                for segment in segments:
                    if "transmitted" in segment:
                        transmitted = int(segment.strip().split(" ")[0])
                    elif "received" in segment:
                        received = int(segment.strip().split(" ")[0])
                    elif "packet loss" in segment:
                        packet_loss = int(segment.strip().split(" ")[0][:-1])
                    elif "time" in segment:
                        time = int(segment.strip().split(" ")[1][:-2])

        avg_ping_time = ping_cumulative_time / received

        return PingStats(transmitted, received, packet_loss, time, avg_ping_time)
