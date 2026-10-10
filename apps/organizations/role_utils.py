OWN_ACTIONS = ("view", "change", "delete")


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
