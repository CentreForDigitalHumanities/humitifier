class HumitifierAgentError(Exception):

    @classmethod
    def name(cls):
        return cls.__class__.__name__


class InvalidScanConfigurationError(HumitifierAgentError):
    pass


class MissingRequiredFactError(InvalidScanConfigurationError):
    def __init__(self, message, artefact_name, *args):
        super().__init__(message, *args)
        self.artefact_name = artefact_name


class FatalCollectorError(HumitifierAgentError):
    pass
