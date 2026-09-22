from __future__ import annotations

import argparse
import os

import firebase_admin
from firebase_admin import auth, credentials


def main() -> None:
    parser = argparse.ArgumentParser(description="Assign production DermCareAI tenant claims to a Firebase clinician.")
    parser.add_argument("--uid", required=True)
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--clinic-id", required=True)
    parser.add_argument("--role", action="append", default=[])
    args = parser.parse_args()

    if not os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"):
        raise SystemExit("FIREBASE_SERVICE_ACCOUNT_JSON must be configured for this administrative operation.")

    if not firebase_admin._apps:
        firebase_admin.initialize_app(
            credentials.Certificate(__import__("json").loads(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"]))
        )

    user = auth.get_user(args.uid)
    roles = sorted(set(args.role or user.custom_claims.get("roles", [])))
    claims = dict(user.custom_claims or {})
    claims.update({
        "organization_id": args.organization_id,
        "clinic_id": args.clinic_id,
        "roles": roles,
        "role": roles[0] if roles else "staff",
    })
    auth.set_custom_user_claims(args.uid, claims)
    print(f"Updated Firebase claims for {args.uid}: organization_id={args.organization_id}, clinic_id={args.clinic_id}, roles={roles}")


if __name__ == "__main__":
    main()
