from depdrift.mapping import default_guess, import_names_for


def test_default_guess_simple_names():
    assert default_guess("requests") == "requests"
    assert default_guess("numpy") == "numpy"


def test_default_guess_hyphenated_name():
    assert default_guess("some-package") == "some_package"


def test_import_names_for_known_overrides():
    assert import_names_for("PyYAML") == {"yaml"}
    assert import_names_for("beautifulsoup4") == {"bs4"}
    assert import_names_for("python-dateutil") == {"dateutil"}
    assert import_names_for("scikit-learn") == {"sklearn"}
    assert import_names_for("Pillow") == {"pil"}
    assert import_names_for("opencv-python") == {"cv2"}


def test_import_names_for_unknown_falls_back_to_guess():
    assert import_names_for("some-random-package") == {"some_random_package"}


def test_import_names_for_stub_only_package_is_empty():
    assert import_names_for("types-requests") == set()


def test_import_names_for_is_case_and_separator_insensitive():
    assert import_names_for("pyyaml") == import_names_for("PyYAML")
    assert import_names_for("python_dateutil") == import_names_for("python-dateutil")
