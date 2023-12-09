import json


def get_config_value(config_key: str) -> str:
    """
    Get the setting from the settings.json file.
    Args:
        config_key: The settings string looks like: "DEVICE/LOCATION_ID"
                    with the equivalent json key being [DEVICE"]["LOCATION_ID"]

    Returns: The value of the json key
    Examples: get_setting("DEVICE/LOCATION_ID")

    See Also: config.json
    References: config_example.json

    """
    try:
        with open('config.json', 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("The config.json file was not found. Please create a config.json file in the "
                                "root directory of the project.")

    keys = config_key.split('/')
    value = settings

    try:
        for key in keys:
            value = value[key]
    except KeyError:
        raise KeyError(f"The setting {config_key} was not found in the config.json file. "
                       "Please add the setting to the config.json file.")

    return value
