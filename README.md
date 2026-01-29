<<<<<<< HEAD
## OPD Token Allocation Engine

This project implements a token allocation system for a hospital OPD (Outpatient
Department) using FastAPI.

Doctors operate in fixed time slots (for example: 09–10, 10–11, 11–12), and
each slot has a maximum capacity. Tokens are generated from multiple sources:

- Online booking
- Walk-in (OPD desk)
- Paid priority patients
- Follow-up patients
- Emergency patients

The system must dynamically handle real-world variability such as delays,
cancellations, and emergency insertions.

---

## Prioritisation Logic

Each token source has a priority (higher number = higher priority):

1. Emergency (highest)
2. Paid priority
3. Follow-up
4. Online
5. Walk-in (lowest)

Rules:

- When a slot has free capacity, the request is simply **booked**.
- When a slot is full:
  - If the new patient has **lower or equal priority** than the lowest-priority
    booked patient → they go to the **waitlist** for that slot.
  - If the new patient has **higher priority** → they **bump** the
    lowest-priority booked patient from that slot.

---

## Reallocation, Edge Cases, and Failure Handling

### Bumping and Reallocation

When a patient is bumped out of a full slot by a higher-priority patient:

1. The engine tries to move the bumped patient to the **next available slot**
   of the same doctor that has capacity.
2. If no later slot is available, the bumped patient is placed on the
   **waitlist** for the original slot.

### Cancellations and No-shows

When a booked token is cancelled:

1. The token status becomes `cancelled` and it is removed from the slot.
2. If the slot has a waitlist, the **first waitlisted patient** is promoted:
   - Their status becomes `booked`.
   - They are added to the slot's booked list.

No-shows can be handled in the same way as cancellations by cancelling their
token.

### Failure Handling

- Invalid doctor or token IDs raise validation errors in the domain layer, which
  are translated into HTTP `400` or `404` responses by the API.
- The allocation engine keeps all state in memory, so restarting the API
  clears the state (acceptable for this assignment).

---

## API Design

The FastAPI application exposes the following endpoints:

- `POST /doctors`
  - Create a doctor with a set of time slots and per-slot capacity.
- `GET /doctors`
  - List all doctors.
- `GET /doctors/{doctor_id}/schedule`
  - View the schedule for a doctor: for each slot, shows capacity, booked
    tokens, and waitlist.
- `POST /tokens/book`
  - Request a token for a given doctor, slot index, patient name, and source.
  - Returns:
    - Whether the patient was booked or waitlisted.
    - If someone was bumped, details of the bumped token.
- `POST /tokens/{token_id}/cancel`
  - Cancel a token and, if possible, promote from waitlist.
- `POST /admin/reset`
  - Clear all in-memory data (useful while testing or simulating scenarios).

FastAPI automatically generates interactive documentation at `/docs` (Swagger
UI) and `/redoc`.

---

## Project Structure

- `domain.py` – Core domain model and token allocation engine.
- `main.py` – FastAPI application and REST endpoints.
- `simulation.py` – Script to simulate one OPD day with three doctors.
- `requirements.txt` – Python dependencies.
- `README.md` – Documentation (this file).

---

## Setup and Running

### 1. Create and activate a virtual environment (recommended)

From the project root (for you this is `e:\opd-token-backend`):

```bash
python -m venv .venv
```

On Windows (PowerShell):

```bash
.\.venv\Scripts\Activate.ps1
```

You should see `(.venv)` at the beginning of your terminal prompt.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the API server

```bash
uvicorn main:app --reload
```

Then open your browser at:

- `http://localhost:8000/docs` – interactive API UI (Swagger).
- `http://localhost:8000/redoc` – alternative API docs.

You can use the Swagger UI to:

- Create doctors with `POST /doctors`.
- Book tokens with `POST /tokens/book`.
- View schedules with `GET /doctors/{doctor_id}/schedule`.
- Cancel tokens with `POST /tokens/{token_id}/cancel`.

---

## Simulation of One OPD Day

The assignment requires a simulation of one OPD day with at least three
doctors. This is implemented in `simulation.py`.

To run it:

```bash
python simulation.py
```

What the simulation does:

- Creates 3 doctors (`Dr. A`, `Dr. B`, `Dr. C`) with four hourly slots each.
- Books a mix of online, walk-in, paid-priority, and emergency patients.
- Demonstrates:
  - Enforcing per-slot capacity limits.
  - Prioritisation between different token sources.
  - Bumping lower-priority patients when a higher-priority patient arrives.
  - Waitlisting and promotion from waitlist after a cancellation.
- Prints the final schedule for `Dr. A` showing:
  - Booked tokens in each slot.
  - Remaining waitlisted tokens.

This covers:

- API design and data schema.
- Implementation of the token allocation algorithm.
- Documentation of prioritisation, edge cases, and failure handling.
- A concrete simulation of an OPD day with three doctors.

=======
# OPD-token-allocation-engine
A FastAPI-based backend service that allocates OPD tokens across doctors and time slots, enforcing capacity limits, handling cancellations/emergencies, and prioritizing patients from different sources.
>>>>>>> cb399a2bcb30fa7f0995105831eae3e2720b4d5f
