class HumitifierAgentError(Exception):

    @classmethod
    def name(cls):
        return cls.__class__.__name__


class InvalidScanConfigurationError(HumitifierAgentError):
    pass


class MissingRequiredFactError(InvalidScanConfigurationError):
    pass


class FatalCollectorError(HumitifierAgentError):
    pass
