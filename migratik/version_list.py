from typing import Optional


class VersionList:

    def __init__(self, versions: list[int]):
        self._versions = sorted(versions)
        self._indexes = {version: index for index, version in enumerate(self._versions)}

    def __iter__(self):
        return iter(self._versions)

    def get_for_upgrade(self, current_version: int, version: Optional[int] = None) -> list[int]:
        if current_version > version:
            raise ValueError(
                f"Current version {current_version} is greater "
                f"than upgrade version {version}!"
            )

        current_version_index = self._indexes[current_version]

        if version is not None:
            version_index = self._indexes[version]

            return self._versions[current_version_index + 1:version_index + 1]

        return self._versions[current_version_index + 1:]

    def get_for_downgrade(self, current_version: int, version: int) -> list[int]:
        if current_version < version:
            raise ValueError(
                f"Current version {current_version} is smaller "
                f"than downgrade version {version}!"
            )

        current_version_index = self._indexes[current_version]
        version_index = self._indexes[version]

        return self._versions[current_version_index:version_index:-1]
