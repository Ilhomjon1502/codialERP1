"""Ma'lumotlarga kirish doirasi (CLAUDE.md 6.3): Admin va Bosh menejer — barcha filiallar, qolganlar — o'z filiallari."""

from .permissions import is_top


def branch_ids(user):
    """None — cheklovsiz (barcha filiallar), aks holda foydalanuvchi filiallari to'plami. So'rov davomida keshlanadi."""
    if is_top(user):
        return None
    cache = getattr(user, "_branch_ids_cache", None)
    if cache is None:
        cache = set(user.branches.values_list("id", flat=True))
        user._branch_ids_cache = cache
    return cache


def scope_branch(qs, user, field="branch"):
    ids = branch_ids(user)
    return qs if ids is None else qs.filter(**{f"{field}__in": ids})


def in_scope(user, branch_id):
    ids = branch_ids(user)
    return ids is None or branch_id in ids
