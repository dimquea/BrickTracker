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


# Make sense of string supposed to contain a minifigure ID
def parse_minifig(figure: str, /) -> str:
    # Minifigure format is typically fig-XXXXXX
    # We'll accept with or without the 'fig-' prefix
    figure = figure.strip()

    if not figure.startswith('fig-'):
        # Try to add the prefix if it's just numbers
        if figure.isdigit():
            figure = 'fig-{figure}'.format(figure=figure.zfill(6))
        else:
            raise ErrorException('Minifigure "{figure}" must start with "fig-"'.format(
                figure=figure,
            ))

    # Validate format: fig-XXXXXX where X can be digits or letters
    parts = figure.split('-')
    if len(parts) != 2 or parts[0] != 'fig':
        raise ErrorException('Invalid minifigure format "{figure}". Expected format: fig-XXXXXX'.format(
            figure=figure,
        ))

    return figure
