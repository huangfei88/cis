# CIS — API Documentation

Base URL: `https://<host>/api/v1`

All endpoints (except `/auth/login` and `/auth/register`) require:
```
Authorization: Bearer <access_token>
```

---

## Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register new user |
| POST | `/auth/login` | No | Get access + refresh token |
| POST | `/auth/refresh` | No | Rotate tokens |
| POST | `/auth/logout` | Yes | Revoke access token |

### POST /auth/register
```json
{ "username": "alice", "email": "alice@example.com", "password": "s3cr3t!!" }
```
Response `201`:
```json
{ "message": "Registration successful", "user_id": "<uuid>" }
```

### POST /auth/login
```json
{ "username": "alice", "password": "s3cr3t!!" }
```
Response `200`:
```json
{ "access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 900 }
```

---

## Scripts

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/scripts/` | any | List approved scripts |
| POST | `/scripts/` | any | Submit script for review |
| GET | `/scripts/{id}` | any | Get script details |
| DELETE | `/scripts/{id}` | owner/admin | Delete script |
| POST | `/scripts/{id}/review` | reviewer/admin | Approve or reject |

### Script Status Lifecycle
```
pending → under_review → approved
                       → rejected
```

---

## Tasks

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| POST | `/tasks/` | any | Create and enqueue task |
| GET | `/tasks/` | any | List my tasks |
| GET | `/tasks/{id}` | owner/admin | Get task + logs |

### POST /tasks/
```json
{ "script_id": "<uuid>", "parameters": { "key": "value" } }
```

---

## Admin

All require `admin` role unless noted.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/users` | List all users |
| PUT | `/admin/users/{id}/role` | Change role |
| GET | `/admin/audit-logs` | Audit log viewer |
| GET | `/admin/tasks` | All tasks |
| GET | `/admin/scripts/pending` | Pending scripts (reviewer+) |

---

## Error Format

```json
{ "detail": "Error message" }
```

Common status codes: `400`, `401`, `403`, `404`, `409`, `422`, `500`
