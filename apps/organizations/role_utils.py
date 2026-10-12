from functools import lru_cache

from django.apps import apps

OWN_ACTIONS = ("view", "change", "delete")


EXCLUDED_APPS = {
    "accounts"
}  # global data, not something an org role should control


@lru_cache(maxsize=1)
def assignable_apps():
    return [
        c.label
        for c in apps.get_app_configs()
        if c.name.startswith("apps.") and c.label not in EXCLUDED_APPS
    ]


def grantable_keys(membership):
    """Permissions this member may hand out: what they hold, plus the _own variant of each view/change/delete."""
    if membership.role is None:
        return set()

    held = set(
        membership.role.permissions.values_list("content_type__app_label", "codename")
    )
    grantable = set(held)
    for app, code in held:
        action, _, rest = code.partition("_")
        if action in OWN_ACTIONS and not rest.startswith("own_"):
            grantable.add((app, f"{action}_own_{rest}"))
    return grantable
