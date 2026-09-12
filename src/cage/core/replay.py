from cage.core.attempt import Attempt


def create_replay_attempt(
    *,
    previous_attempt: Attempt,
    attempt_id: str,
) -> Attempt:
    if not isinstance(previous_attempt, Attempt):
        raise TypeError("previous_attempt must be an Attempt")

    if attempt_id == previous_attempt.attempt_id:
        raise ValueError(
            "replay must create a new attempt identity"
        )

    return Attempt(
        attempt_id=attempt_id,
        consequence=previous_attempt.consequence,
        previous_attempt_id=previous_attempt.attempt_id,
    )