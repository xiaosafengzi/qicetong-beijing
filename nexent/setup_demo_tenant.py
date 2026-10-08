"""Create an idempotent tenant administrator account for the Nexent browser UI."""
from __future__ import annotations

import json

import httpx

from connect_qicetong import ROOT, load_access, request


TENANT_NAME = "企策通演示租户"
ADMIN_EMAIL = "qicetong.admin@nexent.com"


def main() -> None:
    su_email, password, _ = load_access(prefer_demo=False)
    with httpx.Client(timeout=60, trust_env=False) as client:
        session = request(client, "POST", "/user/signin", json={"email": su_email, "password": password})
        client.headers["Authorization"] = "Bearer " + session["data"]["session"]["access_token"]

        tenant_rows = request(
            client, "POST", "/tenants/tenant-list", json={"page": 1, "page_size": 100}
        ).get("data", [])
        tenant = next((item for item in tenant_rows if item.get("tenant_name") == TENANT_NAME), None)
        if tenant is None:
            tenant = request(client, "POST", "/tenants", json={"tenant_name": TENANT_NAME})["data"]
        tenant_id = tenant["tenant_id"]

        signin = client.post(
            "http://127.0.0.1:5010/user/signin",
            json={"email": ADMIN_EMAIL, "password": password},
        )
        if signin.status_code >= 400:
            invitation = request(
                client,
                "POST",
                "/invitations",
                json={"tenant_id": tenant_id, "code_type": "ADMIN_INVITE", "capacity": 1},
            )["data"]
            signup = client.post(
                "http://127.0.0.1:5010/user/signup",
                json={
                    "email": ADMIN_EMAIL,
                    "password": password,
                    "invite_code": invitation["invitation_code"],
                    "auto_login": False,
                },
            )
            if signup.status_code >= 400:
                raise RuntimeError(f"Tenant admin signup failed: HTTP {signup.status_code}: {signup.text[:300]}")

        access_path = ROOT / "runtime/nexent/demo-access.txt"
        access_path.write_text(
            f"Email: {ADMIN_EMAIL}\nPassword: {password}\nTenant: {TENANT_NAME}\nTenant ID: {tenant_id}\n",
            encoding="utf-8",
        )
        print(json.dumps({"tenant": TENANT_NAME, "tenant_id": tenant_id, "email": ADMIN_EMAIL}, ensure_ascii=False))


if __name__ == "__main__":
    main()
