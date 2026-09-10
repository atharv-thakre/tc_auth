from fastapi import Depends
from ..exceptions.error import AccountStatusError, PermissionDeniedError


class StatusDeps:
    def __init__(self, auth_deps):
        self.auth_deps = auth_deps

    def require(
        self,
        status: str,
    ):
        def dependency(
            current: dict = Depends(
                self.auth_deps.get_current
            ),
        ):
            account = current.get("account") if isinstance(current, dict) else None
            if not account or not isinstance(account, dict):
                raise AccountStatusError(status=None, required=status)

            account_status = account.get("status")
            if account_status != status:
                raise AccountStatusError(
                    status=account_status,
                    required=status,
                )

            return account

        return dependency

    def allow(
        self,
        *statuses: str,
    ):
        def dependency(
            current: dict = Depends(
                self.auth_deps.get_current
            ),
        ):
            account = current.get("account") if isinstance(current, dict) else None
            if not account or not isinstance(account, dict):
                raise AccountStatusError(status=None, required=statuses)

            account_status = account.get("status")
            if account_status not in statuses:
                raise AccountStatusError(
                    status=account_status,
                    required=statuses,
                )

            return account

        return dependency

    def block(
        self,
        *statuses: str,
    ):
        def dependency(
            current: dict = Depends(
                self.auth_deps.get_current
            ),
        ):
            account = current.get("account") if isinstance(current, dict) else None
            if not account or not isinstance(account, dict):
                raise AccountStatusError(status=None, message="Account status is not permitted")

            account_status = account.get("status")
            if account_status in statuses:
                raise AccountStatusError(
                    status=account_status,
                    message=f"Status '{account_status}' is blocked",
                )

            return account

        return dependency