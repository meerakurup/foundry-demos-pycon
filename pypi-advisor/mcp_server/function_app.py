"""
PyPI Auditor MCP Server — Azure Functions
------------------------------------------
Exposes 4 MCP tools via the Azure Functions MCP extension:
  - get_package_info
  - check_vulnerabilities
  - compare_packages
  - get_changelog

Deploy as an Azure Function App. MCP clients (Foundry agents, VS Code, etc.)
connect at: https://<FUNCTION_APP_NAME>.azurewebsites.net/runtime/webhooks/mcp
"""

import json
import logging
from datetime import datetime, timezone

import azure.functions as func
import httpx

app = func.FunctionApp()


# ---------------------------------------------------------------------------
# Tool property definitions (JSON strings for MCP tool triggers)
# ---------------------------------------------------------------------------

GET_PACKAGE_INFO_PROPS = json.dumps([
    {
        "propertyName": "package_name",
        "propertyType": "string",
        "description": "The name of the PyPI package to look up",
        "isRequired": True,
    }
])

CHECK_VULNERABILITIES_PROPS = json.dumps([
    {
        "propertyName": "package_name",
        "propertyType": "string",
        "description": "The name of the PyPI package",
        "isRequired": True,
    },
    {
        "propertyName": "version",
        "propertyType": "string",
        "description": "The pinned version to check for CVEs",
        "isRequired": True,
    },
])

COMPARE_PACKAGES_PROPS = json.dumps([
    {
        "propertyName": "package_a",
        "propertyType": "string",
        "description": "First package name",
        "isRequired": True,
    },
    {
        "propertyName": "package_b",
        "propertyType": "string",
        "description": "Second package name",
        "isRequired": True,
    },
])

GET_CHANGELOG_PROPS = json.dumps([
    {
        "propertyName": "package_name",
        "propertyType": "string",
        "description": "The name of the PyPI package",
        "isRequired": True,
    },
    {
        "propertyName": "limit",
        "propertyType": "integer",
        "description": "Max number of recent releases to return (default 10)",
        "isRequired": False,
    },
])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pypi_fetch(package_name: str) -> dict | None:
    url = f"https://pypi.org/pypi/{package_name}/json"
    with httpx.Client(timeout=10) as client:
        r = client.get(url)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


def _osv_fetch(package_name: str, version: str) -> list[dict]:
    """Query OSV.dev for known vulnerabilities."""
    payload = {
        "version": version,
        "package": {"name": package_name, "ecosystem": "PyPI"},
    }
    with httpx.Client(timeout=10) as client:
        r = client.post("https://api.osv.dev/v1/query", json=payload)
        r.raise_for_status()
        return r.json().get("vulns", [])


def _months_since(date_str: str) -> int:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        return delta.days // 30
    except Exception:
        return -1


def _get_args(context) -> dict:
    """Parse MCP tool trigger context and return the arguments dict."""
    content = json.loads(context)
    return content.get("arguments", {})


# ---------------------------------------------------------------------------
# Tool 1: get_package_info
# ---------------------------------------------------------------------------

@app.mcp_tool_trigger(
    arg_name="context",
    tool_name="get_package_info",
    description="Get PyPI metadata for a Python package: latest version, release date, license, author, and Python version support.",
    tool_properties=GET_PACKAGE_INFO_PROPS,
)
def get_package_info(context) -> str:
    args = _get_args(context)
    package_name = args.get("package_name", "").strip().lower()

    if not package_name:
        return json.dumps({"error": "package_name is required"})

    data = _pypi_fetch(package_name)
    if not data:
        return json.dumps({"error": f"Package '{package_name}' not found on PyPI"})

    info = data["info"]
    releases = data.get("releases", {})
    latest_version = info["version"]
    latest_files = releases.get(latest_version, [])
    upload_time = latest_files[0]["upload_time"] if latest_files else "unknown"

    result = {
        "name": info["name"],
        "latest_version": latest_version,
        "latest_release_date": upload_time,
        "months_since_last_release": _months_since(upload_time),
        "summary": info.get("summary", ""),
        "license": info.get("license", "unknown"),
        "home_page": info.get("home_page") or info.get("project_url", ""),
        "author": info.get("author", ""),
        "requires_python": info.get("requires_python", ""),
        "total_versions": len(releases),
    }
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Tool 2: check_vulnerabilities
# ---------------------------------------------------------------------------

@app.mcp_tool_trigger(
    arg_name="context",
    tool_name="check_vulnerabilities",
    description="Check a specific package version against the OSV.dev vulnerability database. Returns known CVEs with severity and fix versions.",
    tool_properties=CHECK_VULNERABILITIES_PROPS,
)
def check_vulnerabilities(context) -> str:
    args = _get_args(context)
    package_name = args.get("package_name", "").strip().lower()
    version = args.get("version", "").strip()

    if not package_name or not version:
        return json.dumps({"error": "package_name and version are required"})

    vulns = _osv_fetch(package_name, version)

    formatted = []
    for v in vulns:
        aliases = v.get("aliases", [])
        cve_ids = [a for a in aliases if a.startswith("CVE-")]

        fixed_in = []
        for affected in v.get("affected", []):
            for rng in affected.get("ranges", []):
                for event in rng.get("events", []):
                    if "fixed" in event:
                        fixed_in.append(event["fixed"])

        formatted.append({
            "id": v.get("id"),
            "cve_ids": cve_ids,
            "summary": v.get("summary", ""),
            "severity": v.get("database_specific", {}).get("severity", "UNKNOWN"),
            "published": v.get("published", ""),
            "fixed_in_versions": list(set(fixed_in)),
            "details_url": f"https://osv.dev/vulnerability/{v.get('id')}",
        })

    result = {
        "package": package_name,
        "version_checked": version,
        "vulnerability_count": len(formatted),
        "vulnerabilities": formatted,
        "safe": len(formatted) == 0,
    }
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Tool 3: compare_packages
# ---------------------------------------------------------------------------

@app.mcp_tool_trigger(
    arg_name="context",
    tool_name="compare_packages",
    description="Side-by-side comparison of two PyPI packages: versions, activity, license, and Python support. Useful for evaluating alternatives.",
    tool_properties=COMPARE_PACKAGES_PROPS,
)
def compare_packages(context) -> str:
    args = _get_args(context)
    pkg_a = args.get("package_a", "").strip().lower()
    pkg_b = args.get("package_b", "").strip().lower()

    if not pkg_a or not pkg_b:
        return json.dumps({"error": "package_a and package_b are required"})

    data_a = _pypi_fetch(pkg_a)
    data_b = _pypi_fetch(pkg_b)

    def summarise(data: dict | None, name: str) -> dict:
        if not data:
            return {"name": name, "found": False}
        info = data["info"]
        releases = data.get("releases", {})
        latest_version = info["version"]
        latest_files = releases.get(latest_version, [])
        upload_time = latest_files[0]["upload_time"] if latest_files else "unknown"
        return {
            "name": info["name"],
            "found": True,
            "latest_version": latest_version,
            "last_release_date": upload_time,
            "months_since_last_release": _months_since(upload_time),
            "total_versions": len(releases),
            "license": info.get("license", "unknown"),
            "requires_python": info.get("requires_python", ""),
            "summary": info.get("summary", ""),
            "home_page": info.get("home_page") or info.get("project_url", ""),
        }

    result = {
        "package_a": summarise(data_a, pkg_a),
        "package_b": summarise(data_b, pkg_b),
    }
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Tool 4: get_changelog
# ---------------------------------------------------------------------------

@app.mcp_tool_trigger(
    arg_name="context",
    tool_name="get_changelog",
    description="Get the last N release versions with dates for a PyPI package. Shows how actively maintained it is and what changed recently.",
    tool_properties=GET_CHANGELOG_PROPS,
)
def get_changelog(context) -> str:
    args = _get_args(context)
    package_name = args.get("package_name", "").strip().lower()
    limit = int(args.get("limit", 10))

    if not package_name:
        return json.dumps({"error": "package_name is required"})

    data = _pypi_fetch(package_name)
    if not data:
        return json.dumps({"error": f"Package '{package_name}' not found on PyPI"})

    releases = data.get("releases", {})

    versioned = []
    for version, files in releases.items():
        if not files:
            continue
        upload_time = files[0].get("upload_time", "")
        if upload_time:
            versioned.append({"version": version, "released": upload_time})

    versioned.sort(key=lambda x: x["released"], reverse=True)
    recent = versioned[:limit]

    info = data["info"]
    project_urls = info.get("project_urls") or {}
    changelog_url = (
        project_urls.get("Changelog")
        or project_urls.get("CHANGELOG")
        or project_urls.get("History")
        or project_urls.get("Release Notes")
        or ""
    )

    result = {
        "package": info["name"],
        "latest_version": info["version"],
        "recent_releases": recent,
        "changelog_url": changelog_url,
    }
    return json.dumps(result)
