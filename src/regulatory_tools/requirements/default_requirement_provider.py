from .requirement_provider import RequirementProvider


class NullRequirementProvider(RequirementProvider):
    """
    Default provider when no requirements are supplied.
    """

    def get(self, key: str) -> str | None:
        return None
