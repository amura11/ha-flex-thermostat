import pytest
from custom_components.flex_thermostat.switch_manager import SwitchManager


def test_entity_id_returns_id():
    # Arrange
    entity_id = "my_fake_entity_123"
    sut = SwitchManager(entity_id)

    # Act
    result = sut.entity_id

    # Assert
    assert entity_id == result


def test_is_active_throws_error_when_uninitialized():
    # Arrange
    entity_id = "my_fake_entity_123"
    sut = SwitchManager(entity_id)

    # Act/Assert
    with pytest.raises(RuntimeError) as error:
        result = sut.is_active


def test_is_enabled_true_when_entity_id_present():
    # Arrange
    entity_id = "my_fake_entity_123"
    sut = SwitchManager(entity_id)

    # Act
    result = sut.is_enabled

    # Assert
    assert True == result


def test_is_enabled_false_when_entity_id_none():
    # Arrange
    sut = SwitchManager(None)

    # Act
    result = sut.is_enabled

    # Assert
    assert False == result
