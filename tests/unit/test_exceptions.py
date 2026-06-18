from shared.exceptions import NotFoundError, PermissionDeniedError, ValidationError


def test_not_found_has_correct_status():
    err = NotFoundError("file missing")
    assert err.status_code == 404
    assert err.code == "NOT_FOUND"
    assert str(err) == "file missing"


def test_permission_denied():
    err = PermissionDeniedError("no access")
    assert err.status_code == 403


def test_detail_defaults_to_empty_dict():
    err = ValidationError("bad input")
    assert err.detail == {}
