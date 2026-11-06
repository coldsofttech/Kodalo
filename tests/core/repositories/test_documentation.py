from kodalo.core.repositories.documentation import find_documentation, is_secret
from kodalo.core.repositories.models import Entry


def test_finds_documentation_files_and_docs_folder() -> None:
    entries = [
        Entry("README.md", "file"),
        Entry("CHANGELOG.md", "file"),
        Entry("Contributing.md", "file"),
        Entry("LICENSE", "file"),
        Entry("SECURITY.md", "file"),
        Entry("docs", "dir"),
        Entry("docs/readme.md", "file"),
    ]
    found = find_documentation(entries)
    assert found.readmes == ("README.md",)
    assert found.docs_dir == "docs"
    assert found.changelog == "CHANGELOG.md"
    assert found.contributing == "Contributing.md"
    assert found.license_file == "LICENSE"
    assert found.security == "SECURITY.md"
    assert found.code_of_conduct == ""


def test_nothing_found_gives_empty_values() -> None:
    found = find_documentation([Entry("src", "dir")])
    assert found.readmes == ()
    assert found.docs_dir == ""
    assert found.license_file == ""


def test_secret_looking_names() -> None:
    assert is_secret(".env.local")
    assert is_secret("config/server.pem")
    assert not is_secret("pyproject.toml")
