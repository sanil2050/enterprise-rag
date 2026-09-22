from unittest.mock import Mock

from app.retrieval.access_control import get_authorized_document_ids


def test_authorized_document_ids_are_returned_for_role():
    db = Mock()

    db.execute.return_value.fetchall.return_value = [
        (1,),
        (2,),
        (5,),
    ]

    result = get_authorized_document_ids(db, "employee")

    assert result == [1, 2, 5]

    db.execute.assert_called_once()

    args, kwargs = db.execute.call_args

    assert args[1] == {"role": "employee"}
    assert kwargs == {}


def test_role_is_parameterized_not_interpolated():
    db = Mock()

    db.execute.return_value.fetchall.return_value = []

    malicious_role = "' OR 1=1 --"

    result = get_authorized_document_ids(db, malicious_role)

    assert result == []

    args, kwargs = db.execute.call_args

    assert args[1] == {"role": malicious_role}
    assert kwargs == {}

    statement = args[0]

    assert malicious_role not in statement.text