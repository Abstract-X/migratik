

class MigratikError(Exception):
    pass


class MigrationError(MigratikError):
    pass


class MigrationPathError(MigratikError):
    pass


class MigrationParsingError(MigratikError):
    pass


class MigrationTableError(MigratikError):
    pass


class ConfigError(MigratikError):
    pass
