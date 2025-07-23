import json
import os


def get_config_value(config_key: str) -> str:
    """
    Get the setting from the config.json file.
    Args:
        config_key: The settings string looks like: "DEVICE/LOCATION_ID"
                    with the equivalent json key being [DEVICE"]["LOCATION_ID"]

    Returns: The value of the json key
    Examples: get_config_value("DEVICE/LOCATION_ID")

    See Also: config.json
    References: config_example.json

    """
    env_var = "_".join(config_key.split("/")).upper()
    try:
        with open('config.json', 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        env_value = os.getenv(env_var)
        if env_value is not None:
            return env_value
        raise FileNotFoundError(
            "The config.json file was not found and environment variable "
            f"{env_var} is not set."
        )

    keys = config_key.split('/')
    value = settings

    try:
        for key in keys:
            value = value[key]
    except KeyError:
        env_value = os.getenv(env_var)
        if env_value is not None:
            return env_value
        raise KeyError(
            f"The setting {config_key} was not found in the config.json file and "
            f"environment variable {env_var} is not set."
        )

    return value
