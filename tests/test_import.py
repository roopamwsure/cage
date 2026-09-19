def test_package_imports() -> None:
    import cage

    assert cage is not None


def test_cage_config_is_exported_from_package_root() -> None:
    from cage import CAGEConfig
    from cage.config import CAGEConfig as ConfigModuleCAGEConfig

    assert CAGEConfig is ConfigModuleCAGEConfig


def test_nonfunctional_cage_facade_is_not_exported() -> None:
    import cage

    assert not hasattr(cage, "CAGE")