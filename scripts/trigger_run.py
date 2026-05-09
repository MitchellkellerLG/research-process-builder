"""
Trigger Trigger.dev tasks via Management API and poll for completion.

Usage:
    py scripts/trigger_run.py                          # trigger all three tasks
    py scripts/trigger_run.py --task game-signals-weekly
    py scripts/trigger_run.py --task product-launches-ph-daily
    py scripts/trigger_run.py --task product-launches-news-daily
    py scripts/trigger_run.py --check <run_id>         # poll an existing run
"""
import json, os, sys, time, argparse, requests
from pathlib import Path
from dotenv import dotenv_values

_env = {
    **dotenv_values(Path(__file__).parent.parent.parent / ".env"),
    **dotenv_values(Path(__file__).parent.parent / ".env"),
    **os.environ,
}

TRIGGER_SECRET_KEY = _env.get("TRIGGER_SECRET_KEY") or _env.get("TRIGGER_ACCESS_TOKEN", "")
SUPABASE_URL = _env.get("SUPABASE_PROJECT_URL") or _env.get("SUPABASE_URL", "")
SUPABASE_KEY = _env.get("SUPABASE_KEY") or _env.get("SUPABASE_SERVICE_ROLE_KEY") or _env.get("SUPABASE_ANON_KEY", "")

API = "https://api.trigger.dev/api/v1"
HEADERS = {"Authorization": f"Bearer {TRIGGER_SECRET_KEY}", "Content-Type": "application/json"}

ALL_TASKS = ["game-signals-weekly", "product-launches-ph-daily", "product-launches-news-daily"]


def check_table_exists(table: str) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}?select=id&limit=1",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=10,
        )
        return r.status_code != 404
    except Exception:
        return False


def trigger_task(task_id: str) -> str | None:
    r = requests.post(
        f"{API}/tasks/{task_id}/trigger",
        headers=HEADERS,
        json={"payload": {}, "options": {}},
        timeout=15,
    )
    if r.status_code == 200:
        run_id = r.json().get("id")
        print(f"  OK  {task_id} -> run {run_id}")
        return run_id
    else:
        print(f"  FAIL {task_id}: {r.status_code} {r.text[:200]}")
        return None


def get_run_status(run_id: str) -> dict:
    for version in ("v3", "v2", "v1"):
        r = requests.get(
            f"https://api.trigger.dev/api/{version}/runs/{run_id}",
            headers=HEADERS,
            timeout=10,
        )
        if r.ok:
            return r.json()
    return {}


def poll_run(run_id: str, task_id: str, timeout_s: int = 300) -> dict:
    deadline = time.time() + timeout_s
    last_status = ""
    while time.time() < deadline:
        data = get_run_status(run_id)
        status = data.get("status", "UNKNOWN")
        if status != last_status:
            elapsed = int(timeout_s - (deadline - time.time()))
            print(f"  [{elapsed:3d}s] {task_id}: {status}")
            last_status = status
        if status in ("COMPLETED", "FAILED", "CRASHED", "CANCELED", "TIMED_OUT", "INTERRUPTED"):
            return data
        time.sleep(10)
    return {"status": "POLL_TIMEOUT"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="Specific task ID to trigger")
    parser.add_argument("--check", help="Poll an existing run ID")
    parser.add_argument("--cancel", help="Cancel a run by ID")
    args = parser.parse_args()

    if not TRIGGER_SECRET_KEY:
        sys.exit("TRIGGER_SECRET_KEY / TRIGGER_ACCESS_TOKEN not found in .env")

    # Check an existing run
    if args.check:
        data = get_run_status(args.check)
        print(json.dumps(data, indent=2, default=str))
        return

    if getattr(args, "cancel", None):
        for version in ("v3", "v2", "v1"):
            r = requests.post(
                f"https://api.trigger.dev/api/{version}/runs/{args.cancel}/cancel",
                headers=HEADERS, timeout=10,
            )
            if r.ok:
                print(f"Canceled run {args.cancel} (via {version}): {r.json()}")
                return
        print(f"Cancel failed for {args.cancel}")
        return

    # Pre-flight: check product_launches table
    print("Pre-flight checks...")
    pl_exists = check_table_exists("product_launches")
    if pl_exists:
        print("  OK  product_launches table exists")
    else:
        print("  WARN product_launches table NOT found — PH + news pipelines will fail Supabase push")
        print("       Run trigger/supabase/migrations/003_product_launches.sql in Supabase dashboard first")
        print()

    tasks = [args.task] if args.task else ALL_TASKS
    print(f"\nTriggering {len(tasks)} task(s)...")
    runs: dict[str, str] = {}
    for task_id in tasks:
        run_id = trigger_task(task_id)
        if run_id:
            runs[task_id] = run_id

    if not runs:
        sys.exit("No tasks triggered successfully")

    print(f"\nPolling {len(runs)} run(s) (max 5 min each)...")
    results: dict[str, dict] = {}
    for task_id, run_id in runs.items():
        print(f"\n--- {task_id} (run: {run_id}) ---")
        result = poll_run(run_id, task_id, timeout_s=300)
        results[task_id] = result
        status = result.get("status", "?")
        output = result.get("output")
        if output:
            print(f"  Output: {json.dumps(output, indent=4, default=str)}")
        error = result.get("error")
        if error:
            print(f"  Error: {json.dumps(error, indent=4, default=str)[:500]}")
        print(f"  => {status}")

    print("\n" + "=" * 50)
    print("Summary:")
    for task_id, result in results.items():
        status = result.get("status", "?")
        icon = "OK " if status == "COMPLETED" else "FAIL"
        print(f"  {icon}  {task_id}: {status}")

    dashboard_url = "https://cloud.trigger.dev"
    print(f"\nDashboard: {dashboard_url}")


if __name__ == "__main__":
    main()
