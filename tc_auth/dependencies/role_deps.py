from fastapi import Depends

from ..exceptions.error import PermissionDeniedError


class RoleDeps:
    def __init__(self, auth_deps):
        self.auth_deps = auth_deps

    def require(
        self,
        role: str,
    ):
        def dependency(
            current=Depends(self.auth_deps.get_current_user),
        ):
            user = current.get("account") if isinstance(current, dict) else None
            if not user or not isinstance(user, dict):
                raise PermissionDeniedError(current=None, required=role, field="role")

            user_role = user.get("role")

            if user_role != role:
                raise PermissionDeniedError(
                    current=user_role,
                    required=role,
                    field="role",
                )

            return user

        return dependency

    def allow(
        self,
        *roles: str,
    ):
        def dependency(
            current=Depends(self.auth_deps.get_current_user),
        ):
            user = current.get("account") if isinstance(current, dict) else None
            if not user or not isinstance(user, dict):
                raise PermissionDeniedError(current=None, required=roles, field="role")

            user_role = user.get("role")

            if user_role not in roles:
                raise PermissionDeniedError(
                    current=user_role,
                    required=roles,
                    field="role",
                )

            return user

        return dependency

    def block(
        self,
        *roles: str,
    ):
        def dependency(
            current=Depends(self.auth_deps.get_current_user),
        ):
            user = current.get("account") if isinstance(current, dict) else None
            if not user or not isinstance(user, dict):
                raise PermissionDeniedError(current=None, field="role", message="Permission denied for role")

            user_role = user.get("role")

            if user_role in roles:
                raise PermissionDeniedError(
                    current=user_role,
                    field="role",
                    message=f"Role '{user_role}' is blocked",
                )

            return user

        return dependency