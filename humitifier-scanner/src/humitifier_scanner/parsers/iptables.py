import ipaddress
import re

from humitifier_common.artefacts import (
    IPTablesChain,
    IPTablesPortAccess,
    IPTableRules,
)

_Network = ipaddress.IPv4Network | ipaddress.IPv6Network

_ANY_SOURCE = "0.0.0.0/0"
_ANY_NETWORK = ipaddress.ip_network(_ANY_SOURCE)
_ANY_INTERFACE = "*"


class _IPTablesCoverage:
    """Keeps track of which source networks already got a verdict from an
    earlier iptables rule, per input interface.

    Rules bound to a specific interface only cover traffic on that interface,
    while rules without an interface cover traffic on every interface.
    """

    def __init__(self):
        self._covered: dict[str, list[_Network]] = {}

    def add(self, networks: list[_Network], interface: str) -> None:
        self._covered.setdefault(interface, []).extend(networks)

    def remaining(self, networks: list[_Network], interface: str) -> list[_Network]:
        """Return the parts of the given networks that are not covered yet
        for traffic on the given interface.
        """
        networks = self.subtract(networks, self._covered.get(_ANY_INTERFACE, []))
        if interface != _ANY_INTERFACE:
            networks = self.subtract(networks, self._covered.get(interface, []))
        return networks

    def covers_everything(self) -> bool:
        return not self.remaining([_ANY_NETWORK], _ANY_INTERFACE)

    @staticmethod
    def subtract(networks: list[_Network], exclude: list[_Network]) -> list[_Network]:
        for excluded in exclude:
            result = []
            for network in networks:
                if network.version != excluded.version or not network.overlaps(
                    excluded
                ):
                    result.append(network)
                elif network.subnet_of(excluded):
                    continue
                else:
                    result.extend(network.address_exclude(excluded))
            networks = result
            if not networks:
                break
        return networks

    @staticmethod
    def intersect(left: list[_Network], right: list[_Network]) -> list[_Network]:
        result = []
        for a in left:
            for b in right:
                if a.version != b.version or not a.overlaps(b):
                    continue
                # Networks either nest or are disjoint; keep the smaller one
                result.append(a if a.subnet_of(b) else b)
        return result


class IPTablesPortAccessSummarizer:
    ALLOW_TARGETS = ("ACCEPT",)
    DENY_TARGETS = ("DROP", "REJECT")
    RETURN_TARGET = "RETURN"
    PORT_PROTOCOLS = ("tcp", "udp", "all")

    # Matches '[tcp|udp] dpt:22', 'dpts:1000:2000', 'multiport dports 80,443'
    _PORT_RE = re.compile(r"\bdpts?:(\S+)|\bdports?\s+(\S+)")
    _STATE_RE = re.compile(r"\b(?:ct)?state\s+(\S+)")

    @classmethod
    def summarize(cls, chains: list[IPTablesChain]) -> list[IPTablesPortAccess]:
        """Build a per-port overview of allowed/denied sources from the
        INPUT chain.

        For every destination port/protocol that is mentioned in the rules, the
        INPUT chain is walked in order like iptables would do for a new
        connection to that port: the first rule that matches a given source
        decides. Rules (or the parts of them) that are shadowed by an earlier
        rule are not reported, jumps into custom chains are followed and the
        default policy of the chain is applied to whatever is left over.

        Only source address, input interface, protocol, destination port and
        connection state are taken into account; other matches (limits, owner,
        mac, ...) are ignored.
        """
        chain_map = {chain.chain: chain for chain in chains}
        input_chain = chain_map.get("INPUT")
        if input_chain is None:
            return []

        summaries = []
        for port, protocol in cls._collect_port_keys(input_chain, chain_map):
            summary = IPTablesPortAccess(port=port, protocol=protocol)
            decided = _IPTablesCoverage()

            cls._walk_chain(
                chain=input_chain,
                chain_map=chain_map,
                port=port,
                protocol=protocol,
                decided=decided,
                summary=summary,
                scope_networks=[_ANY_NETWORK],
                scope_source=_ANY_SOURCE,
                scope_interface=_ANY_INTERFACE,
                visited=frozenset({input_chain.chain}),
            )

            # Whatever was not matched by any rule falls back to the policy
            if not decided.covers_everything():
                if input_chain.default_policy in cls.ALLOW_TARGETS:
                    cls._record_verdict(summary, True, _ANY_SOURCE, _ANY_INTERFACE)
                elif input_chain.default_policy in cls.DENY_TARGETS:
                    cls._record_verdict(summary, False, _ANY_SOURCE, _ANY_INTERFACE)

            if _ANY_SOURCE in summary.denied_from:
                summary.denied_from = [_ANY_SOURCE]

            summaries.append(summary)

        return sorted(
            summaries,
            key=lambda s: (s.port is not None, cls._port_sort_key(s.port), s.protocol),
        )

    @classmethod
    def _collect_port_keys(
        cls,
        chain: IPTablesChain,
        chain_map: dict[str, IPTablesChain],
        visited: frozenset[str] = frozenset(),
    ) -> list[tuple[str | None, str]]:
        """Return every (port, protocol) combination that is mentioned in the
        given chain and in the custom chains it jumps to, in order of first
        appearance.
        """
        visited = visited | {chain.chain}
        keys: dict[tuple[str | None, str], None] = {}

        for rule in chain.rules:
            if rule.prot in cls.PORT_PROTOCOLS and cls._matches_new_connections(rule):
                for port in cls._extract_ports(rule.options):
                    if port is not None and rule.prot == "all":
                        # Ports only make sense for tcp/udp
                        continue
                    keys.setdefault((port, rule.prot), None)

            if rule.target in chain_map and rule.target not in visited:
                for key in cls._collect_port_keys(
                    chain_map[rule.target], chain_map, visited
                ):
                    keys.setdefault(key, None)

        return list(keys)

    @classmethod
    def _walk_chain(
        cls,
        chain: IPTablesChain,
        chain_map: dict[str, IPTablesChain],
        port: str | None,
        protocol: str,
        decided: "_IPTablesCoverage",
        summary: IPTablesPortAccess,
        scope_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
        scope_source: str,
        scope_interface: str,
        visited: frozenset[str],
    ) -> None:
        """Walk a chain in order for traffic to the given port/protocol,
        restricted to the sources/interface that jumped into this chain.

        Every source that gets a final verdict is added to ``decided`` so
        later rules no longer apply to it, mimicking iptables' first-match
        behaviour. Sources hitting RETURN (or the end of the chain) fall back
        to the calling chain.
        """
        # Sources that RETURNed from this chain; they are no longer matched by
        # the remaining rules in this chain, but are still undecided
        returned = _IPTablesCoverage()

        for rule in chain.rules:
            if not cls._rule_applies_to(rule, port, protocol):
                continue

            interface = cls._combine_interfaces(scope_interface, rule.in_)
            if interface is None:
                continue

            rule_networks = cls._parse_networks(rule.source)
            if rule_networks is None:
                continue

            networks = _IPTablesCoverage.intersect(scope_networks, rule_networks)
            networks = decided.remaining(networks, interface)
            networks = returned.remaining(networks, interface)
            if not networks:
                # Fully shadowed by earlier rules
                continue

            # Report the most specific source spec we have
            source = rule.source
            if source == _ANY_SOURCE:
                source = scope_source

            if rule.target in cls.ALLOW_TARGETS:
                cls._record_verdict(summary, True, source, interface)
                decided.add(networks, interface)
            elif rule.target in cls.DENY_TARGETS:
                cls._record_verdict(summary, False, source, interface)
                decided.add(networks, interface)
            elif rule.target == cls.RETURN_TARGET:
                returned.add(networks, interface)
            elif rule.target in chain_map and rule.target not in visited:
                cls._walk_chain(
                    chain=chain_map[rule.target],
                    chain_map=chain_map,
                    port=port,
                    protocol=protocol,
                    decided=decided,
                    summary=summary,
                    scope_networks=networks,
                    scope_source=source,
                    scope_interface=interface,
                    visited=visited | {rule.target},
                )
            # LOG, comments, unknown targets, etc. are non-terminating

    @classmethod
    def _rule_applies_to(
        cls, rule: IPTableRules, port: str | None, protocol: str
    ) -> bool:
        """Check if a rule can match a new connection to the given
        port/protocol combination.
        """
        if rule.prot not in cls.PORT_PROTOCOLS:
            return False

        if rule.prot != "all" and rule.prot != protocol:
            return False

        # A rule for a specific protocol does not cover 'all protocols'
        if protocol == "all" and rule.prot != "all":
            return False

        if not cls._matches_new_connections(rule):
            return False

        if not cls._destination_applies(rule.destination):
            return False

        rule_ports = cls._extract_ports(rule.options)
        if rule_ports == [None]:
            return True

        # A rule for specific ports does not cover 'all ports'
        if port is None:
            return False

        return any(cls._port_in_spec(port, spec) for spec in rule_ports)

    @classmethod
    def _matches_new_connections(cls, rule: IPTableRules) -> bool:
        # Rules that only match existing connections do not open ports
        state_match = cls._STATE_RE.search(rule.options)
        return not state_match or "NEW" in state_match.group(1).split(",")

    @classmethod
    def _destination_applies(cls, destination: str) -> bool:
        """Check if a rule's destination can apply to traffic addressed to
        this host. Rules for multicast/broadcast destinations (or with
        unparsable netmasks) are skipped; a specific unicast destination is
        assumed to be one of the host's own addresses.
        """
        if destination == _ANY_SOURCE:
            return True

        networks = cls._parse_networks(destination)
        if networks is None:
            return False

        return not any(
            network.is_multicast or network.is_reserved for network in networks
        )

    @classmethod
    def _combine_interfaces(cls, scope_interface: str, interface: str) -> str | None:
        """Combine the interface of a jump rule with the one of a rule in the
        target chain; None if they conflict.
        """
        interface = interface or _ANY_INTERFACE
        if scope_interface == _ANY_INTERFACE:
            return interface
        if interface == _ANY_INTERFACE or interface == scope_interface:
            return scope_interface
        return None

    @classmethod
    def _parse_networks(
        cls, source: str
    ) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network] | None:
        """Parse an iptables source spec into a list of networks; None if it
        cannot be parsed (e.g. non-contiguous netmasks).
        """
        negated = source.startswith("!")
        source = source.lstrip("!").strip()

        _address, _sep, mask = source.partition("/")
        if "." in mask:
            # iptables shows dotted masks as netmasks, which may be
            # non-contiguous (e.g. 0.0.0.255); python would happily read
            # those as hostmasks, which means something else entirely
            try:
                mask_bits = int(ipaddress.IPv4Address(mask))
            except ValueError:
                return None
            host_bits = ~mask_bits & 0xFFFFFFFF
            if host_bits & (host_bits + 1):
                return None

        try:
            network = ipaddress.ip_network(source, strict=False)
        except ValueError:
            return None

        if negated:
            return _IPTablesCoverage.subtract([_ANY_NETWORK], [network])
        return [network]

    @classmethod
    def _record_verdict(
        cls,
        summary: IPTablesPortAccess,
        allowed: bool,
        source: str,
        interface: str,
    ) -> None:
        if interface != _ANY_INTERFACE:
            source = f"{source}@{interface}"

        target_list = summary.allowed_from if allowed else summary.denied_from
        if source not in target_list:
            target_list.append(source)

        if allowed and source == _ANY_SOURCE:
            summary.default_open = True
        elif not allowed and source == _ANY_SOURCE:
            summary.default_closed = True

    @classmethod
    def _extract_ports(cls, options: str) -> list[str | None]:
        """Return the destination ports a rule applies to; [None] if the rule
        is not restricted to a port.
        """
        match = cls._PORT_RE.search(options)
        if not match:
            return [None]

        port_spec = match.group(1) or match.group(2)
        return [port for port in port_spec.split(",") if port]

    @classmethod
    def _port_in_spec(cls, port: str, spec: str) -> bool:
        """Check if a port (or port range) falls completely within a port spec
        from a rule. Both are formatted as either 'port' or 'start:end'.
        """
        port_range = cls._parse_port_range(port)
        spec_range = cls._parse_port_range(spec)
        if port_range is None or spec_range is None:
            return port == spec

        return spec_range[0] <= port_range[0] and port_range[1] <= spec_range[1]

    @staticmethod
    def _parse_port_range(port: str) -> tuple[int, int] | None:
        start, _, end = port.partition(":")
        try:
            start_num = int(start) if start else 0
            end_num = int(end) if end else (start_num if not _ else 65535)
        except ValueError:
            return None
        return start_num, end_num

    @staticmethod
    def _port_sort_key(port: str | None) -> int:
        if port is None:
            return -1
        try:
            # Port ranges are formatted as 'start:end'
            return int(port.split(":")[0])
        except ValueError:
            return 0


def summarize_port_access(
    chains: list[IPTablesChain],
) -> list[IPTablesPortAccess]:
    """Build a per-port overview of allowed/denied sources from the
    INPUT chain.
    """
    return IPTablesPortAccessSummarizer.summarize(chains)
