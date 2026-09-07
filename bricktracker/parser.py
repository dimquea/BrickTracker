from .exceptions import ErrorException


# Make sense of string supposed to contain a set ID
def parse_set(set: str, /) -> str:
    number, _, version = set.partition('-')

    # Set number can be alphanumeric (e.g., "McDR6US", "10312", "COMCON035")
    # Just validate it's not empty
    if not number or number.strip() == '':
        raise ErrorException('Set number cannot be empty')

    # Clean up the number (trim whitespace)
    number = number.strip()

    # Version defaults to 1 if not provided
    if version == '':
        version = '1'

    # Version must be a valid number (but preserve leading zeros for minifigures)
    try:
        version_int = int(version)
    except Exception:
        raise ErrorException('Version "{version}" is not a number'.format(
            version=version,
        ))

    if version_int < 0:
        raise ErrorException('Version "{version}" should be positive'.format(
            version=version,
        ))

    # Preserve original version string to keep leading zeros (important for minifigures like fig-000484)
    return '{number}-{version}'.format(number=number, version=version)


# Make sense of string supposed to contain a minifigure ID
def parse_minifig(figure: str, /) -> str:
    # Идентификаторы фигурок BrickLink произвольные: sw1029, oct054, x30,
    # col123. Общей формы у них нет, поэтому проверять нечего кроме того,
    # что строка не пуста. Прежняя проверка на префикс fig- относилась к
    # нумерации Rebrickable.
    figure = figure.strip()

    if not figure:
        raise ErrorException('Minifigure number cannot be empty')

    return figure
