from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional


class TokenSource(str, Enum):
    EMERGENCY = "emergency"
    PAID_PRIORITY = "paid_priority"
    FOLLOW_UP = "follow_up"
    ONLINE = "online"
    WALK_IN = "walk_in"


class TokenStatus(str, Enum):
    BOOKED = "booked"
    WAITLISTED = "waitlisted"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

PRIORITY_ORDER = {
    TokenSource.EMERGENCY: 5,
    TokenSource.PAID_PRIORITY: 4,
    TokenSource.FOLLOW_UP: 3,
    TokenSource.ONLINE: 2,
    TokenSource.WALK_IN: 1,
}


@dataclass
class Token:
    id: int
    patient_name: str
    source: TokenSource
    doctor_id: int
    slot_index: int
    status: TokenStatus = TokenStatus.BOOKED


@dataclass
class Slot:
    index: int
    label: str
    capacity: int
    token_ids: List[int] = field(default_factory=list)
    waitlist_ids: List[int] = field(default_factory=list)


@dataclass
class Doctor:
    id: int
    name: str
    slots: List[Slot]


@dataclass
class AllocationResult:
    token: Token
    allocated_slot_index: Optional[int]
    bumped_token: Optional[Token] = None
    waitlisted: bool = False


class TokenEngine:
    """
    In-memory token allocation engine.

    Responsibilities:
    - Enforces per-slot capacity.
    - Prioritizes sources using PRIORITY_ORDER.
    - On full slots, can bump lower-priority patients to later slots or waitlist.
    - Handles cancellations and promotes from waitlist.
    """

    def __init__(self) -> None:
        self.doctors: Dict[int, Doctor] = {}
        self.tokens: Dict[int, Token] = {}
        self._next_doctor_id = 1
        self._next_token_id = 1

    def reset(self) -> None:
        self.doctors.clear()
        self.tokens.clear()
        self._next_doctor_id = 1
        self._next_token_id = 1

    def create_doctor(
        self,
        name: str,
        slot_labels: List[str],
        capacity_per_slot: int,
    ) -> Doctor:
        doctor_id = self._next_doctor_id
        self._next_doctor_id += 1

        slots = [
            Slot(index=i, label=label, capacity=capacity_per_slot)
            for i, label in enumerate(slot_labels)
        ]
        doctor = Doctor(id=doctor_id, name=name, slots=slots)
        self.doctors[doctor_id] = doctor
        return doctor

    def list_doctors(self) -> List[Doctor]:
        return list(self.doctors.values())

    def get_doctor(self, doctor_id: int) -> Doctor:
        if doctor_id not in self.doctors:
            raise ValueError(f"Doctor {doctor_id} not found")
        return self.doctors[doctor_id]

    def book_token(
        self,
        doctor_id: int,
        slot_index: int,
        patient_name: str,
        source: TokenSource,
    ) -> AllocationResult:
        doctor = self.get_doctor(doctor_id)

        if slot_index < 0 or slot_index >= len(doctor.slots):
            raise ValueError("Invalid slot index")

        token_id = self._next_token_id
        self._next_token_id += 1

        token = Token(
            id=token_id,
            patient_name=patient_name,
            source=source,
            doctor_id=doctor_id,
            slot_index=slot_index,
            status=TokenStatus.BOOKED,
        )
        self.tokens[token_id] = token

        slot = doctor.slots[slot_index]
        if len(slot.token_ids) < slot.capacity:
            slot.token_ids.append(token_id)
            return AllocationResult(
                token=token,
                allocated_slot_index=slot_index,
                bumped_token=None,
                waitlisted=False,
            )

        lowest_token_id = min(
            slot.token_ids,
            key=lambda tid: PRIORITY_ORDER[self.tokens[tid].source],
        )
        lowest_token = self.tokens[lowest_token_id]

        if PRIORITY_ORDER[source] <= PRIORITY_ORDER[lowest_token.source]:
            token.status = TokenStatus.WAITLISTED
            slot.waitlist_ids.append(token_id)
            return AllocationResult(
                token=token,
                allocated_slot_index=None,
                bumped_token=None,
                waitlisted=True,
            )

        slot.token_ids.remove(lowest_token_id)
        slot.token_ids.append(token_id)

        new_index = self._find_next_available_slot(doctor, start=slot_index + 1)
        if new_index is not None:
            new_slot = doctor.slots[new_index]
            lowest_token.slot_index = new_index
            new_slot.token_ids.append(lowest_token.id)
        else:
            lowest_token.status = TokenStatus.WAITLISTED
            slot.waitlist_ids.append(lowest_token.id)

        return AllocationResult(
            token=token,
            allocated_slot_index=slot_index,
            bumped_token=lowest_token,
            waitlisted=False,
        )

    def _find_next_available_slot(self, doctor: Doctor, start: int) -> Optional[int]:
        for idx in range(start, len(doctor.slots)):
            slot = doctor.slots[idx]
            if len(slot.token_ids) < slot.capacity:
                return idx
        return None

    def cancel_token(self, token_id: int) -> Dict[str, Optional[Token]]:
        if token_id not in self.tokens:
            raise ValueError(f"Token {token_id} not found")

        token = self.tokens[token_id]
        doctor = self.get_doctor(token.doctor_id)
        slot = doctor.slots[token.slot_index]

        if token_id in slot.token_ids:
            slot.token_ids.remove(token_id)

        token.status = TokenStatus.CANCELLED
        promoted_token: Optional[Token] = None
        if slot.waitlist_ids:
            promoted_id = slot.waitlist_ids.pop(0)
            promoted_token = self.tokens[promoted_id]
            promoted_token.status = TokenStatus.BOOKED
            promoted_token.slot_index = slot.index
            slot.token_ids.append(promoted_id)

        return {"cancelled": token, "promoted": promoted_token}

    def get_schedule_for_doctor(self, doctor_id: int) -> Dict:
        doctor = self.get_doctor(doctor_id)
        result_slots = []

        for slot in doctor.slots:
            booked_tokens = [self.tokens[tid] for tid in slot.token_ids]
            waitlist_tokens = [self.tokens[wid] for wid in slot.waitlist_ids]

            result_slots.append(
                {
                    "index": slot.index,
                    "label": slot.label,
                    "capacity": slot.capacity,
                    "booked": [asdict(t) for t in booked_tokens],
                    "waitlist": [asdict(t) for t in waitlist_tokens],
                }
            )

        return {
            "doctor_id": doctor.id,
            "doctor_name": doctor.name,
            "slots": result_slots,
        }

