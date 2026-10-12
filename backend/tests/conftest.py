import itertools

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.references.models import Branch

PASSWORD = "Sinov-Parol-2026!"
_n = itertools.count(1)


@pytest.fixture
def branch(db):
    return Branch.objects.create(name="Emirat")


@pytest.fixture
def other_branch(db):
    return Branch.objects.create(name="Andijon")


@pytest.fixture
def make_user(db, branch):
    def make(role="ADMINISTRATOR", branches=None, password=PASSWORD, **extra):
        i = next(_n)
        u = User.objects.create_user(
            email=extra.pop("email", f"user{i}@codial.test"), password=password, full_name=extra.pop("full_name", f"Xodim {i}"),
            role=Role.objects.get(code=role), **extra,
        )
        if role not in ("ADMIN", "BOSH_MENEJER"):
            u.branches.set(branches if branches is not None else [branch])
        return u

    return make


@pytest.fixture
def api():
    def client(user=None):
        c = APIClient()
        if user:
            c.force_login(user)
        return c

    return client
