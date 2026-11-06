"""Every bundled parser config reads its kind of file."""

import pytest

from kodalo.core.repositories.configs.manifest import ManifestConfig, load_configs, match_config
from kodalo.core.repositories.parsers.manifest import MAX_NAMES, ManifestDetails, parse_manifest

CONFIGS = load_configs().configs


def _config(file_name: str) -> ManifestConfig:
    matched = match_config(file_name, CONFIGS)
    assert matched is not None
    return matched[0]


def _parse(file_name: str, text: str) -> ManifestDetails:
    return parse_manifest(text, _config(file_name))


def test_all_bundled_configs_load() -> None:
    result = load_configs()

    assert result.problems == ()
    assert len(result.configs) == 17


def test_pyproject_uv_and_poetry() -> None:
    uv = _parse(
        "pyproject.toml",
        '[project]\nname = "app"\nversion = "1.0"\ndependencies = ["typer>=0.9", "rich"]\n'
        '[dependency-groups]\ndev = ["pytest>=8", {include-group = "lint"}]\nlint = ["ruff"]\n',
    )
    assert (uv.package_name, uv.version) == ("app", "1.0")
    assert uv.dependencies == ("typer", "rich")
    assert uv.dev_dependencies == ("pytest", "ruff")

    poetry = _parse(
        "pyproject.toml",
        '[tool.poetry]\nname = "p"\n[tool.poetry.dependencies]\npython = "^3.11"\nrequests = "*"\n',
    )
    assert poetry.package_name == "p"
    assert poetry.dependencies == ("requests",)


def test_requirements_dev_and_plain() -> None:
    plain = _parse("requirements.txt", "# c\nflask==2.0\n-r other.txt\nrequests[security]>=2\n")
    assert plain.dependencies == ("flask", "requests")
    dev = _parse("requirements-dev.txt", "pytest\n")
    assert dev.dev_dependencies == ("pytest",)
    assert dev.dependencies == ()


def test_package_json_and_composer() -> None:
    js = _parse(
        "package.json",
        '{"name": "web", "version": "2.0.0", "dependencies": {"react": "1"}, '
        '"devDependencies": {"vite": "5"}}',
    )
    assert (js.package_name, js.version) == ("web", "2.0.0")
    assert (js.dependencies, js.dev_dependencies) == (("react",), ("vite",))

    php = _parse(
        "composer.json", '{"name": "a/b", "require": {"php": "^8", "ext-json": "*", "x/y": "1"}}'
    )
    assert php.dependencies == ("x/y",)


def test_cargo_with_workspace_version() -> None:
    cargo = _parse(
        "Cargo.toml",
        '[package]\nname = "c"\nversion = { workspace = true }\n[dependencies]\nserde = "1"\n'
        '[dev-dependencies]\ncriterion = "0.5"\n',
    )
    assert cargo.package_name == "c"
    assert cargo.version is None
    assert (cargo.dependencies, cargo.dev_dependencies) == (("serde",), ("criterion",))


def test_go_mod() -> None:
    go = _parse(
        "go.mod",
        "module github.com/me/app\n\ngo 1.21\n\nrequire (\n\tgithub.com/a/b v1.2.3\n"
        "\tgithub.com/c/d v0.1.0 // indirect\n)\nrequire github.com/x/y v1.0.0\n",
    )
    assert go.package_name == "github.com/me/app"
    assert go.dependencies == ("github.com/a/b", "github.com/c/d", "github.com/x/y")


def test_maven_with_namespace_and_test_scope() -> None:
    pom = _parse(
        "pom.xml",
        '<project xmlns="http://maven.apache.org/POM/4.0.0"><artifactId>app</artifactId>'
        "<version>1.0</version><dependencies>"
        "<dependency><artifactId>guava</artifactId></dependency>"
        "<dependency><artifactId>junit</artifactId><scope>test</scope></dependency>"
        "</dependencies></project>",
    )
    assert (pom.package_name, pom.version) == ("app", "1.0")
    assert pom.dependencies == ("guava",)
    assert pom.dev_dependencies == ("junit",)


def test_gradle() -> None:
    gradle = _parse(
        "build.gradle.kts",
        'dependencies {\n  implementation("org.x:lib:1.0")\n  testImplementation "org.y:t:2"\n}\n',
    )
    assert gradle.dependencies == ("org.x:lib",)
    assert gradle.dev_dependencies == ("org.y:t",)


def test_dotnet_project() -> None:
    proj = _parse(
        "App.csproj",
        "<Project><PropertyGroup><AssemblyName>App</AssemblyName></PropertyGroup>"
        '<ItemGroup><PackageReference Include="Newtonsoft.Json" Version="13" /></ItemGroup>'
        "</Project>",
    )
    assert proj.package_name == "App"
    assert proj.dependencies == ("Newtonsoft.Json",)


def test_gemfile_and_pubspec() -> None:
    gems = _parse("Gemfile", "source 'x'\ngem 'rails', '~> 7'\ngem \"puma\"\n")
    assert gems.dependencies == ("rails", "puma")
    pub = _parse(
        "pubspec.yaml",
        "name: app\nversion: 1.0.0\ndependencies:\n  flutter:\n    sdk: flutter\n  http: ^1.0.0\n"
        "dev_dependencies:\n  lints: ^3.0.0\nflutter:\n  uses-material-design: true\n",
    )
    assert (pub.package_name, pub.version) == ("app", "1.0.0")
    assert pub.dependencies == ("flutter", "http")
    assert pub.dev_dependencies == ("lints",)


def test_swift_mix_and_cmake() -> None:
    swift = _parse(
        "Package.swift",
        'let package = Package(name: "Lib", dependencies: [\n'
        '  .package(url: "https://github.com/apple/swift-log.git", from: "1.0.0"),\n])',
    )
    assert (swift.package_name, swift.dependencies) == ("Lib", ("swift-log",))
    mix = _parse(
        "mix.exs",
        'app: :demo,\nversion: "0.1.0"\n[{:phoenix, "~> 1.7"}, {:ecto, "~> 3"}]\n',
    )
    assert (mix.package_name, mix.version) == ("demo", "0.1.0")
    assert mix.dependencies == ("phoenix", "ecto")
    cmake = _parse("CMakeLists.txt", "project(Demo VERSION 2.1)\nfind_package(Boost REQUIRED)\n")
    assert (cmake.package_name, cmake.version, cmake.dependencies) == ("Demo", "2.1", ("Boost",))


def test_invalid_file_gives_a_warning_and_no_details() -> None:
    details = _parse("package.json", "{ not json")

    assert details.package_name is None
    assert details.dependencies == ()
    assert details.warnings


def test_dependencies_are_capped_with_a_warning() -> None:
    many = ", ".join(f'"p{i}": "1"' for i in range(MAX_NAMES + 5))
    details = _parse("package.json", '{"dependencies": {' + many + "}}")

    assert len(details.dependencies) == MAX_NAMES
    assert "only the first 50" in details.warnings[0]


def test_lockfiles_are_matched_and_setup_py_has_no_details() -> None:
    matched = match_config("web/package-lock.json", CONFIGS)
    assert matched is not None
    assert matched[1] is True
    assert _parse("setup.py", "from setuptools import setup").dependencies == ()


@pytest.mark.parametrize("name", ["pyproject.toml", "package.json", "go.mod", "pom.xml"])
def test_empty_file_is_fine(name: str) -> None:
    assert _parse(name, "").dependencies == ()
