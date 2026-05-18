import argparse

from data_service import run_daily_update, seed_demo_data
from db import init_db, log_update


def main():
    parser = argparse.ArgumentParser(description="Lottery MVP data updater")
    parser.add_argument("--seed-demo", action="store_true", help="Seed demo data")
    parser.add_argument("--run-once", action="store_true", help="Run one update cycle")
    args = parser.parse_args()

    init_db()
    try:
        if args.seed_demo:
            count = seed_demo_data()
            print(f"Seeded {count} demo rows.")
        elif args.run_once:
            count = run_daily_update()
            print(f"Updated {count} rows from official sources when available.")
        else:
            parser.print_help()
    except Exception as exc:
        log_update("cli_update", "failed", str(exc))
        raise


if __name__ == "__main__":
    main()
