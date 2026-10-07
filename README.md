# Spotlight

A desktop inventory management application. Track items, assign owners,
log stock in/out, and filter by owner / category / status / location —
combinably, via a single smart search box.

## Status

**MVP complete**, with a login system, dark theme, stock tracking, and
export on top. All four core screens (Dashboard, Inventory, Users,
Settings) are fully implemented:

- **Login screen** — single super-admin account, no role tiers. Default
  login: `admin` / `admin123`. Forces a password change on first login
  (no way to skip except logging back out). Password stored as a salted
  PBKDF2-SHA256 hash (stdlib `hashlib`, no extra dependency). "Log Out"
  in the sidebar footer returns to the login screen without closing the
  app. A "Change Password" button is also available anytime afterward.
- **Dashboard** — stat tiles (Total Items, Active, Available,
  Maintenance, Owners), each with a colored icon badge, clickable to jump
  into a pre-filtered Inventory/Users view. An "Items by Category" bar
  chart below, also clickable per bar.
- **Inventory screen**:
  - A single smart search box: plain words search everywhere; `field:value`
    tokens (`owner:`, `category:`, `location:`, `status:`, `id:`) apply
    precise, combinable filters (e.g. `owner:john status:active`)
  - Add / edit / delete items, with duplicate inventory-number validation
  - Background-thread queries (UI never blocks on DB I/O)
  - Results capped at 500 rows with an accurate total count shown — a
    broad search against a very large database can't freeze the UI or
    balloon memory (see "Performance notes" below)
  - **Stock In / Stock Out tracking** — dated, note-able movement log per
    item. Stock Out marks an item Archived; Stock In on an archived item
    restores it to Available. New items auto-log their first "In" entry
    from Date Acquired. A "History" button shows the full log for any item.
  - **Export** — CSV (file save), PDF (formatted report), and Print
    (native print dialog), all respecting the current search and never
    capped at 500 rows like the on-screen table
- **Users screen** — list of owners with live item counts, click-through
  to see everything a user owns, add/edit/delete (delete blocked if the
  user still owns items)
- **Settings screen** — manage Categories and Locations (add/rename/delete,
  each blocked if still in use by an item)
- SQLite database, auto-migrating on every launch — upgrading from an
  older version never requires deleting your data
- **Dark, purple-accented theme** — card-based, with a bundled Inter font
  (SIL OFL licensed) so typography looks identical on every machine
  rather than depending on what's installed
- **Hover/press micro-animations** — buttons and stat tiles animate a
  soft glow shadow on hover and shrink on press, applied globally via one
  event filter rather than wired into every file individually
- **App icon** — a purple rounded-square magnifying glass, generated
  programmatically (not found/licensed artwork)
- Packaging into a standalone `.exe` is implemented and tested — see
  `build_exe.md`

## Requirements

- Python 3.9+ (tested through 3.13)
- See `requirements.txt` (PySide6, SQLAlchemy — pip picks the newest
  compatible build for whatever Python version you have)

## Installation

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running

```bash
python -m app.main
```

On first run, the app seeds a SQLite database at
`~/.spotlight/spotlight.db` with sample inventory data, and creates the
default login account (`admin` / `admin123`).

**Note for a real client deployment:** the sample inventory data (John
Doe / Maria Lopez / Carlos Reyes and a handful of demo items) is meant
for development/testing. If you're handing this off for real use, that
seed data should be removed or the database reset before the client's
first real launch, so they aren't greeted by fictional records.

## Project Structure

```text
spotlight/
├── app/
│   ├── main.py                    # entry point; login/logout loop, theming
│   ├── session.py                 # tracks the currently logged-in account
│   ├── ui/
│   │   ├── main_window.py         # sidebar + stacked screens + account footer
│   │   ├── login_view.py          # login dialog
│   │   ├── change_password_dialog.py
│   │   ├── dashboard_view.py      # stat tiles + category chart
│   │   ├── inventory_view.py      # filter bar + table + stock + export
│   │   ├── item_edit_dialog.py
│   │   ├── stock_movement_dialog.py
│   │   ├── stock_history_dialog.py
│   │   ├── users_view.py
│   │   ├── user_edit_dialog.py
│   │   ├── user_detail_dialog.py
│   │   └── settings_view.py
│   ├── widgets/
│   │   ├── filter_bar.py              # smart search box
│   │   ├── inventory_table_model.py
│   │   ├── users_table_model.py
│   │   ├── reference_list_panel.py    # reusable add/rename/delete list
│   │   ├── stat_tile.py               # stat card + icon badge
│   │   ├── bar_chart.py               # hand-painted category chart
│   │   └── hover_effects.py           # global hover/press animations
│   ├── services/
│   │   ├── item_service.py        # search parsing, filtering, capping
│   │   ├── user_service.py
│   │   ├── settings_service.py
│   │   ├── dashboard_service.py
│   │   ├── auth_service.py        # password hashing, login
│   │   ├── stock_service.py       # stock in/out movement log
│   │   ├── export_service.py      # CSV + PDF/print report
│   │   └── db_worker.py           # background-thread query controller
│   ├── models/
│   │   └── models.py              # Account, User, Category, Location,
│   │                               # Item, StockMovement
│   └── database/
│       ├── engine.py              # engine/session + lightweight migrations
│       └── seed.py                # first-run demo data
├── assets/
│   ├── style.qss                  # dark theme stylesheet
│   ├── icon.ico / icon.png        # app icon
│   └── fonts/Inter.ttf            # bundled font
├── spotlight.spec                 # PyInstaller build spec
├── build_exe.md                   # packaging instructions + findings
├── requirements.txt
├── requirements-build.txt
└── README.md
```

## Database

SQLite, via SQLAlchemy. Key tables:

- `accounts` — login credentials (separate from `users`, which are
  inventory owners, not people who log in)
- `users` — id, name, department, contact, status, created_at
- `categories` / `locations` — id, name
- `items` — id, inventory_number, name, category_id (FK), owner_id (FK),
  location_id (FK), status, serial_number, date_acquired, notes,
  created_at, updated_at
- `stock_movements` — id, item_id (FK), movement_type (In/Out),
  movement_date, notes, created_at — an append-only log, not a single
  "last movement" field, so full history survives multiple in/out cycles

One `User` can own many `Item` records. Deleting an item cleans up its
own `stock_movements`; deleting a user/category/location is blocked if
anything still references it.

## Performance notes

Stress-tested against synthetic databases from 1,000 up to 250,000 items.
Two findings worth knowing if this ever needs to scale further:

1. **Combined filters are cheap at any scale.** `owner:X category:Y
   status:Z` together stayed under 125ms even at 250,000 items, because
   narrowing conditions naturally shrink the result set before any
   expensive work happens.
2. **Unbounded result sets were the actual bottleneck**, not missing
   indexes. An unfiltered search against 250,000 items originally took
   ~9.4 seconds — not from a slow query, but from constructing 250,000
   full ORM objects in Python. Capping results at 500 rows (with a real
   total count from a separate, cheap `COUNT(*)`) brought that down to
   ~108ms and keeps it roughly flat regardless of table size.

If this app is ever expected to hold hundreds of thousands of items with
heavy free-text search traffic, a SQLite FTS5 full-text index would be
the next real upgrade — free-text search is the one remaining path that
grows with table size (~470ms at 250,000 items). Not necessary at
anything under that scale.

## Security notes

The login screen restricts who can *open the app*, but it does not
encrypt or lock down the SQLite file itself — `spotlight.db` is a plain
file on disk, and anyone with direct file access can open it with any
SQLite browser regardless of the app's login. If that matters for your
use case, the login screen alone isn't sufficient; you'd also want OS-level
file permissions or database encryption (e.g. SQLCipher). There's still no
account management UI — no way to add a second account from within the
app (password changes, though, are covered — see above).

## Troubleshooting

- **Blank/empty table on first launch**: the initial query runs on a
  background thread; give it a moment. If it stays empty, check the
  console for an error dialog — query failures surface via `errorRaised`.
- **Reset demo data**: delete `~/.spotlight/spotlight.db` and relaunch.
- **`No matching distribution found for PySide6==...`**: your Python
  version is newer than the pinned PySide6 release supports.
  `requirements.txt` uses a version range rather than a strict pin so
  `pip` picks whatever build matches your Python automatically.
- **Login "doesn't work"**: if pressing Enter right after typing your
  username shows "Enter a username and password," that's a (now fixed)
  bug where Enter in the username field submitted the form before the
  password was typed — update to the latest version. Otherwise, remember
  the forced first-login password change means `admin123` only works
  until you've logged in successfully once.
