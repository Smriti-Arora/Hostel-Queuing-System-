# Hostel Queuing System — Full Project Documentation

Detailed reference for the **Hostel Queuing System**: architecture, roles, routes, models, views, templates, settings, security, and how every major piece works.

---

## 1. What this project is

A **Django web app** for hostel operations:

| Feature | Description |
|---------|-------------|
| Student registry | Register / update / delete hostel students |
| QR codes | Generate QR per student; store PNG **in the database** (BLOB) |
| Gate attendance | Webcam QR scan → Present / Absent with time rules |
| Mess attendance | Webcam QR scan → breakfast / lunch / dinner within time windows |
| Room inventory | Configurable Single / Double / Triple / Four-sitter rooms + capacities |
| Staff roles | Super Admin, Gate Staff, Mess Staff with restricted access |

**Stack:** Django 5.1 · MySQL · WhiteNoise · python-dotenv · qrcode / Pillow · ZXing (browser) · gunicorn (production)

---

## 2. Repository layout

```
Hostel-Queuing-System-/
├── .env                      # Local secrets (NOT committed)
├── .env.example              # Template for env vars
├── .gitignore
├── requirements.txt          # Python dependencies
├── myenv/                    # Virtual environment (local)
├── PROJECT_DOCUMENTATION.md  # This file
└── hostel_queuing/           # Django project root
    ├── manage.py
    ├── media/                # Legacy media path (QR no longer saved as files)
    ├── staticfiles/          # collectstatic output (production)
    ├── hostel_queuing/       # Project package (settings, urls, wsgi)
    │   ├── settings.py
    │   ├── urls.py
    │   ├── wsgi.py
    │   └── asgi.py
    └── hostel_app/           # Main application
        ├── models.py
        ├── views.py
        ├── forms.py
        ├── urls.py
        ├── admin.py
        ├── permissions.py
        ├── context_processors.py
        ├── apps.py
        ├── migrations/
        ├── static/css/app.css
        └── templates/
```

---

## 3. Local setup & run

### 3.1 Prerequisites

- Python 3.10+ (project tested with 3.13 + `myenv`)
- MySQL 8 running locally
- Visual C++ 2013 Redistributable (needed for `pyzbar` / `libzbar` on Windows)

### 3.2 Create DB

```sql
CREATE DATABASE IF NOT EXISTS hostel_queuing
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3.3 Virtualenv + install

```powershell
cd C:\Users\shiva\OneDrive\Documents\GitHub\Hostel-Queuing-System-
python -m venv myenv
.\myenv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Important:** Always activate `myenv` before `runserver`. System Python will miss packages like `whitenoise` / `dotenv`.

### 3.4 Environment (`.env`)

Copy `.env.example` → `.env` and set values. Example local:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=hostel_queuing
DB_USER=root
DB_PASSWORD=your-mysql-password
DB_HOST=localhost
DB_PORT=3306
```

### 3.5 Migrate & run

```powershell
cd hostel_queuing
python manage.py migrate
python manage.py createsuperuser   # if needed
python manage.py runserver
```

App URL: **http://127.0.0.1:8000/**

Default superuser (if created during setup): `admin` / `Admin@7379` — **change in production**.

---

## 4. Access control (roles)

Roles live in `StaffProfile` (`hostel_app/models.py`) linked 1:1 to Django `User`.

| Role code | Display name | Who creates it |
|-----------|--------------|----------------|
| `admin` | Super Admin | Superuser / Django admin; existing `is_superuser` counts as admin |
| `gate` | Gate Staff | Super Admin via **Staff** page |
| `mess` | Mess Staff | Super Admin via **Staff** page |

### 4.1 Permission matrix

| Page / action | Admin | Gate | Mess |
|---------------|:-----:|:----:|:----:|
| Login / Logout | ✅ | ✅ | ✅ |
| Students list / register / edit / delete | ✅ | ❌ | ❌ |
| QR regenerate / QR image | ✅ | ❌ | ❌ |
| Room vacancies | ✅ | ❌ | ❌ |
| Hostel settings (room counts) | ✅ | ❌ | ❌ |
| Manage staff accounts | ✅ | ❌ | ❌ |
| Gate scan | ✅ | ✅ | ❌ |
| Gate attendance logs | ✅ | ✅ | ❌ |
| Mess scan | ✅ | ❌ | ✅ |
| Mess logs | ✅ | ❌ | ✅ |

**Rule:** `@role_required(...)` always allows **admin**. Other roles must be listed explicitly.

### 4.2 Login landing pages

| Role | Redirect after login |
|------|----------------------|
| Admin | `/home/` (students) |
| Gate | `/scan_qr/` |
| Mess | `/mess_entry/` |

Implemented in `permissions.home_url_for_role()`.

### 4.3 How role checks work (`permissions.py`)

```text
get_user_role(user)
  → if is_superuser → "admin"
  → else staff_profile.role
  → else None (login blocked)

role_required("gate")
  → login_required
  → allow if role is admin OR gate
  → else message + redirect to role home
```

### 4.4 Creating staff (Super Admin)

1. Login as admin  
2. Open **Staff** (`/staff/`)  
3. Enter username, password, confirm, role (`Gate Staff` or `Mess Staff`)  
4. Staff login with those credentials  
5. Admin can **Disable / Enable** accounts (`/staff/<id>/toggle/`)

Staff passwords are hashed by Django (`User.set_password` / `create_user`). Never stored plain text.

---

## 5. URL map (all routes)

Project root `hostel_queuing/urls.py`:

- `/admin/` → Django admin site  
- `` → includes `hostel_app.urls`

### 5.1 App routes (`hostel_app/urls.py`)

| URL | Name | View | Access |
|-----|------|------|--------|
| `/` | `login` | `login_view` | Public |
| `/logout/` | `logout` | `logout_view` | Any staff (POST) |
| `/home/` | `student_list` | `student_list` | Admin |
| `/register/` | `register_student` | `register_student` | Admin |
| `/student/<roll>/` | `student_detail` | `student_detail` | Admin |
| `/student/<roll>/qr/` | `student_qr_image` | `student_qr_image` | Admin |
| `/student/delete/<roll>/` | `delete_student` | `delete_student` | Admin |
| `/student/update/<roll>/` | `update_student` | `update_student` | Admin |
| `/generate_qr_code/<roll>/` | `generate_qr_code` | `regenerate_qr_code` | Admin (POST) |
| `/validate_qr_code/` | `validate_qr_code` | `validate_qr_code` | Admin, Gate (POST) |
| `/scan_qr/` | `scan_qr` | `scan_qr` | Admin, Gate |
| `/reset_form/` | `reset_form` | `reset_form` | Admin |
| `/attendance_overview/` | `attendance_overview` | `attendance_overview` | Admin, Gate |
| `/mess_entry/` | `scan_qr_for_mess` | `scan_qr_for_mess` | Admin, Mess |
| `/mess-entries/` | `mess_entry_list` | `mess_entry_list` | Admin, Mess |
| `/vacant-rooms/` | `vacant_rooms` | `vacant_rooms_view` | Admin |
| `/settings/` | `hostel_settings` | `hostel_settings_view` | Admin |
| `/api/available-rooms/` | `available_rooms_api` | `available_rooms_api` | Admin |
| `/staff/` | `manage_staff` | `manage_staff` | Admin |
| `/staff/<user_id>/toggle/` | `toggle_staff_active` | `toggle_staff_active` | Admin (POST) |

---

## 6. Models (database)

File: `hostel_app/models.py`

### 6.1 `StaffProfile`

| Field | Type | Notes |
|-------|------|-------|
| `user` | OneToOne → `auth.User` | `related_name='staff_profile'` |
| `role` | CharField | `admin` / `gate` / `mess` |
| `created_at` | DateTime | auto |

### 6.2 `HostelSettings` (singleton `pk=1`)

Configures room inventory:

| Field | Default | Meaning |
|-------|---------|---------|
| `single_rooms` | 10 | Count of single rooms |
| `double_rooms` | 20 | Count of double rooms |
| `triple_rooms` | 10 | Count of triple rooms |
| `foursitter_rooms` | 5 | Count of four-sitter rooms |
| `single_capacity` | 1 | Students per single |
| `double_capacity` | 2 | Students per double |
| `triple_capacity` | 3 | Students per triple |
| `foursitter_capacity` | 4 | Students per four-sitter |

**Room number scheme:**

| Type | Prefix | Example |
|------|--------|---------|
| Single | `S` | `S01` … `S10` |
| Double | `D` | `D01` … `D20` |
| Triple | `T` | `T01` … |
| FourSitter | `F` | `F01` … |

Helpers:

- `HostelSettings.load()` — get or create singleton  
- `inventory_for(room_type)` — list of room numbers  
- `capacity_for(room_type)` — max occupants  
- `available_rooms(room_type, exclude_roll_no=)` — rooms with free beds (for dropdowns)

### 6.3 `Student`

| Field | Rules |
|-------|--------|
| `uni_roll_no` | PK, exactly 7 digits |
| `name`, `father_name` | required |
| `phone_no`, `father_phone_no` | 10 digits, unique |
| `room_no` | Must exist in settings inventory |
| `room_type` | Single / Double / Triple / FourSitter |
| `hostel_type` | Boys / Girls |
| `state`, `city`, `address`, `branch` | as configured |
| `qr_code` | **BinaryField** — PNG bytes in DB |
| `qr_code_data` | Text payload e.g. `1234567,Name` |

**Validation in `Student.clean()`:**

1. `room_no` must be in configured inventory  
2. `room_type` must match that room’s type  
3. Cannot mix types in same room number  
4. Occupancy cannot exceed capacity for that type  

`qr_code_data_uri` property → base64 data URI if needed.

### 6.4 `Attendance` (gate)

| Field | Notes |
|-------|--------|
| `uni_roll_no` | string (not FK) |
| `date` | day of record |
| `time_in` / `time_out` | optional times |
| `status` | `Present` / `Absent` (default Absent) |

### 6.5 `MessAttendance`

| Field | Notes |
|-------|--------|
| `uni_roll_no` | string |
| `meal` | breakfast / lunch / dinner |
| `date` | auto |
| `status` | default Present |

### 6.6 `MealEntry`

Legacy/alternate meal log (`uni_roll_no`, `meal`, `date`). Kept for admin; main mess flow uses `MessAttendance`.

---

## 7. Views — what each function does

File: `hostel_app/views.py`

### 7.1 Auth

| Function | Behavior |
|----------|----------|
| `login_view` | Django auth form; rejects users with no role; redirects by role |
| `logout_view` | POST logout → login page |

### 7.2 Students (admin)

| Function | Behavior |
|----------|----------|
| `student_list` | List all students |
| `register_student` | Create student + generate QR |
| `update_student` | Edit student (roll disabled) |
| `delete_student` | Confirm + delete |
| `student_detail` | Detail + QR image |
| `student_qr_image` | HTTP response `image/png` from DB blob |
| `regenerate_qr_code` | POST → new PNG in DB, JSON with data URI |
| `reset_form` | Flash + redirect list |
| `available_rooms_api` | JSON list of free rooms for a `room_type` |

### 7.3 QR generation helper

`generate_qr_code(student)`:

1. Payload = `"{uni_roll_no},{name}"`  
2. `qrcode.make` → PNG in memory (`BytesIO`)  
3. Save bytes to `student.qr_code` + text to `qr_code_data`  
4. **No filesystem write**

### 7.4 Gate scan (`scan_qr`)

- **GET:** camera page  
- **POST JSON** `{ "qr_data": "roll,name" }`:
  - Parse roll  
  - Block entry/exit **22:00–07:00** local time  
  - Toggle Present ↔ Absent  
  - Set `time_in` / `time_out`  
  - Response includes `scanned_at` timestamp string  

### 7.5 Mess scan (`scan_qr_for_mess`)

- **GET:** camera + meal select  
- **POST** form: `uni_roll_no`, `meal`  
- Time windows (IST):
  - Breakfast 07:30–09:00  
  - Lunch 12:30–14:00  
  - Dinner 19:30–21:00  
- One mark per student per meal per day  
- Response includes scan timestamp  

### 7.6 Logs & rooms

| Function | Behavior |
|----------|----------|
| `attendance_overview` | Today’s present vs absent lists |
| `mess_entry_list` | All mess rows + meal counts |
| `vacant_rooms_view` | Vacant beds from settings inventory |
| `hostel_settings_view` | Edit room counts / capacities |
| `manage_staff` | Create gate/mess users |
| `toggle_staff_active` | Enable/disable staff `User.is_active` |

### 7.7 Scan timestamps

`_scan_timestamp()` returns:

```python
{
  "scanned_at": "19 Jul 2026, 08:30:15 PM",
  "scanned_time": "08:30:15 PM",
  "scanned_date": "19 Jul 2026",
}
```

Merged into every gate/mess JSON response; UI shows **Scanned at …**.

---

## 8. Forms (`forms.py`)

| Form | Purpose |
|------|---------|
| `LoginForm` | Styled Django `AuthenticationForm` |
| `StaffUserCreateForm` | username, password, confirm, role (gate/mess only); validates password strength; creates `User` + `StaffProfile` |
| `HostelSettingsForm` | Room counts + capacities |
| `StudentForm` | Student fields; `room_no` is a **ChoiceField** filled from `available_rooms()`; JS refreshes options when room type changes |

---

## 9. Templates & UI

Base layout: `templates/base.html`

- Fonts: **Syne** (display) + **Manrope** (body)  
- Styles: `static/css/app.css`  
- Nav links filtered by `is_admin_user` / `is_gate_user` / `is_mess_user` (context processor)

| Template | Page |
|----------|------|
| `login.html` | Sign in |
| `student_list.html` | Student table + regen QR JS |
| `student_form.html` | Register/update + room dropdown AJAX |
| `student_detail.html` | Profile + QR |
| `confirm_delete.html` | Delete confirm |
| `scan_qr.html` | Gate camera (ZXing) |
| `scan_qr_for_mess.html` | Mess camera (ZXing) |
| `attendance_overview.html` | Gate logs |
| `mess_entry_list.html` | Mess logs |
| `vacant_rooms.html` | Vacancy table |
| `hostel_settings.html` | Room settings |
| `manage_staff.html` | Create / disable staff |

Context processor: `hostel_app.context_processors.role_context`  
Exposes: `user_role`, `is_admin_user`, `is_gate_user`, `is_mess_user`, `role_home`.

---

## 10. Settings & security (`settings.py`)

### 10.1 Env-driven config

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Secret key |
| `DJANGO_DEBUG` | `True`/`False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | HTTPS origins |
| `DB_*` | MySQL connection |

### 10.2 Always-on hardening

- `SESSION_COOKIE_HTTPONLY`, `CSRF_COOKIE_HTTPONLY`  
- Session age 8 hours; expire on browser close  
- `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY`  
- WhiteNoise middleware for static files  
- Time zone: `Asia/Kolkata`

### 10.3 When `DEBUG=False`

- SSL redirect, secure cookies, HSTS  
- Compressed manifest static storage  
- Proxy SSL header support  

### 10.4 Production checklist

1. Strong `DJANGO_SECRET_KEY`  
2. `DJANGO_DEBUG=False`  
3. Real `ALLOWED_HOSTS` + CSRF origins  
4. Non-root MySQL user  
5. Change default admin password  
6. `python manage.py collectstatic`  
7. Run with **gunicorn** behind nginx/HTTPS  

```bash
gunicorn hostel_queuing.wsgi:application --bind 0.0.0.0:8000
```

---

## 11. Dependencies (`requirements.txt`)

| Package | Why |
|---------|-----|
| Django | Web framework |
| mysqlclient | Django ↔ MySQL |
| mysql-connector-python | Optional connector (legacy leftover possible) |
| qrcode + Pillow | QR PNG generation |
| openpyxl | Excel (imported historically; not central to current UI) |
| opencv-python, numpy, pyzbar | Image/QR libs (server-side; browser uses ZXing for scans) |
| pytz | IST windows for mess |
| python-dotenv | Load `.env` |
| whitenoise | Serve static in production |
| gunicorn | Production WSGI server |

---

## 12. Migrations history (high level)

| Migration | Change |
|-----------|--------|
| `0001`–`0008` | Student fields evolution |
| `0009` | Removed insecure plaintext `Admin` model |
| `0010` | `qr_code` ImageField → BinaryField (DB storage) |
| `0011` | `HostelSettings` + FourSitter room type |
| `0012` | `StaffProfile` roles |

---

## 13. Django Admin

Registered models: `StaffProfile`, `HostelSettings`, `Student`, `Attendance`, `MessAttendance`, `MealEntry`.

URL: `/admin/` (staff/superuser only).

---

## 14. End-to-end flows

### 14.1 Register student + QR

1. Admin → Register  
2. Choose **room type** → JS calls `/api/available-rooms/?room_type=...`  
3. Choose free **room number**  
4. Save → `Student.clean()` validates capacity  
5. `generate_qr_code()` stores PNG in DB  

### 14.2 Gate attendance

1. Gate staff opens Gate Scan  
2. Camera reads QR `roll,name`  
3. POST `/scan_qr/`  
4. Toggle Present/Absent (unless night lockout)  
5. UI shows message + **Scanned at** time  

### 14.3 Mess attendance

1. Mess staff selects meal  
2. Scan QR → POST `/mess_entry/`  
3. Validates meal window + no duplicate today  
4. Creates `MessAttendance` + shows timestamp  

### 14.4 Create gate/mess user

1. Admin → Staff  
2. Create username/password/role  
3. Staff logs in → only their nav items  

---

## 15. Important files cheat-sheet

| File | Responsibility |
|------|----------------|
| `settings.py` | Env, DB, security, static, logging |
| `models.py` | Data + room rules + QR blob |
| `views.py` | All HTTP logic |
| `forms.py` | Login, student, settings, staff create |
| `permissions.py` | Roles & decorators |
| `context_processors.py` | Template role flags |
| `urls.py` (app) | Route table |
| `static/css/app.css` | Design system |
| `templates/base.html` | Shell + role-aware nav |
| `.env` | Secrets (keep private) |

---

## 16. Common problems

| Symptom | Cause / fix |
|---------|-------------|
| `No module named 'whitenoise'` / `dotenv` | Activate `myenv` before runserver |
| `libzbar-64.dll` error | Install VC++ 2013 x64 redistributable |
| MySQL access denied | Fix `DB_PASSWORD` in `.env` |
| Cannot open `/home/` as gate user | Expected — gate has no student access |
| Room dropdown empty | Set counts on **Settings**; rooms may be full |
| Old QR files in `media/qr_codes/` | Legacy; app now uses DB — regenerate QR |

---

## 17. Default credentials reminder

| Account | Username | Password | Notes |
|---------|----------|----------|-------|
| Super Admin | `admin` | `Admin@7379` | Change immediately for real deploy |
| Gate / Mess | created by admin | set on Staff page | Role-limited |

---

## 18. License / ownership

Project code belongs to the repository owner. This document describes the codebase as of the production-grade upgrade (auth, roles, DB QR storage, hostel room settings, UI redesign).

---

*End of documentation.*
