import keyword


def encode(name: str) -> str:
    def escape(c: str) -> str:
        if c.isidentifier() or c.isdigit() or c == "_":
            return c

        return f"_x{ord(c):02X}_"

    encoded = "".join(escape(c) for c in name)

    if not encoded or not (encoded[0].isalpha() or encoded[0] == "_"):
        encoded = "_" + encoded

    if keyword.iskeyword(encoded):
        encoded = "_" + encoded

    if not encoded.isidentifier():
        raise ValueError(f"Encoding failed: {encoded!r} is not a valid identifier")

    return encoded
