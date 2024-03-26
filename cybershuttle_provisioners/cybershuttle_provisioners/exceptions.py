# custom exceptions
class NoSlurmFlagsFound(Exception):
    pass


class UnknownLoginnode(Exception):
    pass


class UnknownUsername(Exception):
    pass


class SlurmJobFailed(Exception):
    pass


class SlurmJobTimeout(Exception):
    pass


class NoSlurmJobID(Exception):
    pass


class SSHAgentNotRunning(Exception):
    pass


class SSHTimeout(Exception):
    pass


class SSHCommandError(Exception):
    pass


class SSHTunnelCommandError(Exception):
    pass


class SSHConnectionError(Exception):
    pass


class WrongFileType(Exception):
    pass


class NoEditorGiven(Exception):
    pass


class FileAlreadyExists(Exception):
    pass


class RenderTemplateError(Exception):
    pass
