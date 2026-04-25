from abc import ABC, abstractmethod


class RequirementProvider(ABC):
    """
    Abstract interface for resolving requirement IDs.

    Keeps AI pipelines decoupled from project-specific requirement schemes.
    """

    @abstractmethod
    def get(self, key: str) -> str | None:
        """
        Resolve a logical key to a requirement ID.

        Parameters
        ----------
        key : str
            Logical identifier (e.g., 'patient_load_failure')

        Returns
        -------
        str | None
            Requirement ID or None if not defined
        """
        pass

    def require(self, key: str) -> str:
        """
        Same as get(), but raises if missing.
        Useful for strict regulatory mode.
        """
        value = self.get(key)
        if value is None:
            raise ValueError(f"Missing requirement mapping for key: {key}")
        return value
