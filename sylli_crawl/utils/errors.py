"""Project wide error handling."""


class ConsentParseError(ValueError):
    """Could not find correct values to navigate consent form."""


class ParseError(ValueError):
    """Could not find any of the CSS classes/IDs or HTML tags."""


