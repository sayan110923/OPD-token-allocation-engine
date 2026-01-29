from domain import TokenEngine, TokenSource


def run_simulation() -> None:
    """
    Simulate one OPD day with at least 3 doctors.

    Demonstrates:
    - Slot capacity limits.
    - Prioritisation between sources.
    - Bumping lower-priority patients.
    - Waitlisting and promotion after cancellation.
    """
    engine = TokenEngine()

    slot_labels = ["09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00"]
    d1 = engine.create_doctor("Dr. Sayan", slot_labels, capacity_per_slot=5)
    d2 = engine.create_doctor("Dr. Srikrishna", slot_labels, capacity_per_slot=5)
    d3 = engine.create_doctor("Dr. Tanaya", slot_labels, capacity_per_slot=5)

    print("Doctors created:", d1.id, d2.id, d3.id)

    engine.book_token(d1.id, 0, "Alice", TokenSource.ONLINE)
    engine.book_token(d1.id, 0, "Bob", TokenSource.WALK_IN)
    engine.book_token(d1.id, 0, "Charlie", TokenSource.ONLINE)

    res = engine.book_token(d1.id, 0, "David", TokenSource.ONLINE)
    print("David waitlisted?", res.waitlisted)

    res = engine.book_token(d1.id, 0, "Eve (Paid)", TokenSource.PAID_PRIORITY)
    print("Eve allocated at slot", res.allocated_slot_index)
    if res.bumped_token:
        print(
            "Bumped:",
            res.bumped_token.patient_name,
            "now in slot",
            res.bumped_token.slot_index,
            "status",
            res.bumped_token.status,
        )

    res = engine.book_token(d1.id, 0, "Frank (Emergency)", TokenSource.EMERGENCY)
    print("Frank allocated at slot", res.allocated_slot_index)
    if res.bumped_token:
        print(
            "Bumped by emergency:",
            res.bumped_token.patient_name,
            "slot",
            res.bumped_token.slot_index,
            "status",
            res.bumped_token.status,
        )

    cancel_info = engine.cancel_token(1)
    print("Cancelled:", cancel_info["cancelled"].patient_name)
    if cancel_info["promoted"]:
        print("Promoted from waitlist:", cancel_info["promoted"].patient_name)

    schedule = engine.get_schedule_for_doctor(d1.id)
    print("\nFinal schedule for", schedule["doctor_name"])
    for slot in schedule["slots"]:
        print(f"\nSlot {slot['index']} ({slot['label']})")
        print("  Booked:")
        for t in slot["booked"]:
            print(f"    #{t['id']} {t['patient_name']} [{t['source']}] status={t['status']}")
        print("  Waitlist:")
        for t in slot["waitlist"]:
            print(f"    #{t['id']} {t['patient_name']} [{t['source']}] status={t['status']}")


if __name__ == "__main__":
    run_simulation()

