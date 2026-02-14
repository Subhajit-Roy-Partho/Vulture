from vulture.db.repositories import canonicalize_question, hash_question


def test_canonicalize_question_normalizes_whitespace_and_case() -> None:
    assert canonicalize_question("  Are   You  Authorized   ") == "are you authorized"


def test_hash_question_is_stable_for_semantic_equivalent_strings() -> None:
    a = hash_question("Are you authorized to work in the United States?")
    b = hash_question("  are you authorized to work in the united states? ")
    assert a == b
