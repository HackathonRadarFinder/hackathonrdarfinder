"""Free Render demo configuration regression. No provider or database access."""
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_render_blueprint_is_free_and_manual_only():
    blueprint = yaml.safe_load((ROOT / "render.staging.yaml").read_text(encoding="utf-8"))
    assert len(blueprint["databases"]) == 1
    database = blueprint["databases"][0]
    assert database["plan"] == "free"
    assert database["ipAllowList"] == []
    assert len(blueprint["services"]) == 2
    assert {s["name"] for s in blueprint["services"]} == {
        "hackathon-radar-demo-api", "hackathon-radar-demo-web"
    }
    for service in blueprint["services"]:
        assert service["type"] == "web"
        assert service["plan"] == "free"
        assert service["branch"] == "develop"
        assert service["autoDeployTrigger"] == "off"
        assert "preDeployCommand" not in service
        assert "disk" not in service
        assert "startCommand" not in service
    api, frontend = blueprint["services"]
    assert api["healthCheckPath"] == "/ready"
    assert "workers.migrate" in api["dockerCommand"]
    assert "uvicorn app.main:app" in api["dockerCommand"]
    values = {variable["key"]: variable for variable in frontend["envVars"]}
    assert values["BACKEND_SCHEME"]["value"] == "https"
    assert values["BACKEND_PORT"]["value"] == "443"
    assert values["BACKEND_HOST"]["fromService"] == {
        "type": "web",
        "name": api["name"],
        "envVarKey": "RENDER_EXTERNAL_HOSTNAME",
    }


def test_nginx_frontend_verifies_external_render_tls():
    nginx = (ROOT / "frontend/nginx.conf").read_text(encoding="utf-8")
    script = (ROOT / "frontend/docker-entrypoint.d/40-radar-upstream.sh").read_text(encoding="utf-8")
    dockerfile = (ROOT / "frontend/Dockerfile").read_text(encoding="utf-8")
    assert "${BACKEND_SCHEME}://${BACKEND_HOST}:${BACKEND_PORT}" in nginx
    assert "proxy_ssl_verify on;" in nginx
    assert "proxy_ssl_server_name on;" in nginx
    assert "proxy_ssl_trusted_certificate /etc/ssl/certs/ca-certificates.crt;" in nginx
    assert "proxy_set_header Host ${BACKEND_HOST};" in nginx
    assert "Cache-Control \"no-store\"" in nginx
    assert "BACKEND_SCHEME=${BACKEND_SCHEME:-http}" in script
    assert "case \"$BACKEND_SCHEME\" in http|https)" in script
    assert "apk add --no-cache ca-certificates" in dockerfile
