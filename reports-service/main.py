import os
from functools import lru_cache

import clickhouse_connect
import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt

KEYCLOAK_INTERNAL_URL = os.getenv("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "reports-realm")
ISSUER = os.getenv("KEYCLOAK_ISSUER", f"http://localhost:8080/realms/{KEYCLOAK_REALM}")
REQUIRED_ROLE = os.getenv("REQUIRED_ROLE", "prothetic_user")

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "reports")

CERTS_URL = f"{KEYCLOAK_INTERNAL_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

app = FastAPI(title="BionicPRO Reports Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["Authorization"],
)


@lru_cache(maxsize=1)
def _jwks() -> dict:
    return httpx.get(CERTS_URL, timeout=5).json()


def _ch_client():
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT, database=CLICKHOUSE_DB
    )


def current_user(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        claims = jwt.decode(
            token,
            _jwks(),
            algorithms=["RS256"],
            issuer=ISSUER,
            options={"verify_aud": False},
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    roles = claims.get("realm_access", {}).get("roles", [])
    if REQUIRED_ROLE not in roles:
        raise HTTPException(status_code=403, detail="Insufficient role")

    username = claims.get("preferred_username")
    if not username:
        raise HTTPException(status_code=401, detail="No subject in token")
    return username


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/reports")
def get_report(period: str | None = None, user_id: str = Depends(current_user)):
    ch = _ch_client()

    max_period = ch.query(
        "SELECT max(period) FROM user_reports WHERE user_id = {u:String}",
        parameters={"u": user_id},
    ).result_rows[0][0]
    if max_period is None:
        raise HTTPException(status_code=404, detail="No processed data for user")

    target = period or str(max_period)
    if target > str(max_period):
        raise HTTPException(status_code=404, detail="Period not processed yet")

    rows = ch.query(
        """
        SELECT user_id, period, full_name, prosthesis_model,
               total_events, avg_response_ms, p95_response_ms,
               movements_count, avg_battery, updated_at
        FROM user_reports
        WHERE user_id = {u:String} AND period = {p:String}
        LIMIT 1
        """,
        parameters={"u": user_id, "p": target},
    )
    if not rows.result_rows:
        raise HTTPException(status_code=404, detail="Report not found")

    keys = rows.column_names
    return dict(zip(keys, rows.result_rows[0]))
