from .exceptions import ErrorException


# Make sense of string supposed to contain a set ID
def parse_set(set: str, /) -> str:
    number, _, version = set.partition('-')

    # Making sure both are integers
    if version == '':
        version = 1

    try:
        number = int(number)
    except Exception:
        raise ErrorException('Number "{number}" is not a number'.format(
            number=number,
        ))

    try:
        version = int(version)
    except Exception:
        raise ErrorException('Version "{version}" is not a number'.format(
            version=version,
        ))

    # Make sure both are positive
    if number < 0:
        raise ErrorException('Number "{number}" should be positive'.format(
            number=number,
        ))

    if version < 0:
        raise ErrorException('Version "{version}" should be positive'.format(  # noqa: E501
            version=version,
        ))

    return '{number}-{version}'.format(number=number, version=version)
