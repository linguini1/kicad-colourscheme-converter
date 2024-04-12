"""
Given a list of colours from a colour scheme (palette), this program will create a KiCad colour scheme that is a
translated version of the original.
"""

__author__ = "Matteo Golin"

from typing import Any, Self, TypeAlias
import json
import math
import re
import argparse
from argparse import FileType
from dataclasses import dataclass

JSON: TypeAlias = dict[str, Any]
HEX_PATTERN: str = r"[0-9a-fA-F]{2}"
DIGIT_PATTERN: str = r"\d"


@dataclass
class Colour:
    red: int
    green: int
    blue: int
    alpha: float

    @staticmethod
    def __validate_colour(colour: int, colour_name: str) -> None:
        """
        Validates that a colour is within the acceptable range for RGB colours. Raises a value error if not.
        """
        if colour < 0 or colour > 255:
            raise ValueError(f"{colour_name.capitalize()} value {colour} not between 0-255")

    def __post_init__(self) -> None:

        if self.alpha < 0.0 or self.alpha > 1.0:
            raise ValueError(f"Alpha {self.alpha} not between 0 and 1.")

        self.__validate_colour(self.red, "red")
        self.__validate_colour(self.green, "green")
        self.__validate_colour(self.blue, "blue")

    @classmethod
    def from_hex_string(cls, hex_val: str) -> Self:
        """Creates a colour from a hex string of format '#AARRGGBB' or '#RRGGBB'."""

        hex_val = hex_val.replace("#", "")  # Remove prefix #

        # Has alpha information
        if len(hex_val) > 6:
            alpha = int(hex_val[:2], 16)
            hex_val = hex_val[2:]
        else:
            alpha = 1.0

        # Parse RGB values
        vals = re.findall(HEX_PATTERN, hex_val)
        return cls(
            alpha=alpha,
            red=int(vals[0], 16),
            green=int(vals[1], 16),
            blue=int(vals[2], 16),
        )

    @classmethod
    def from_rgb_string(cls, rgb_val: str) -> Self:
        """Creates a colour from an RGB string of format 'rgba(r, g, b, a)' or 'rgb(r, g, b)'."""

        # Extract all values
        contents = rgb_val.split("(")[1].split(")")[0]
        vals = contents.split(",")

        if "rgba" not in rgb_val:
            vals.append("1.0")

        return cls(
            red=int(vals[0]),
            green=int(vals[1]),
            blue=int(vals[2]),
            alpha=float(vals[3]),
        )

    def to_hex_string(self) -> str:
        """Returns the string representation of this colour in the format '#aabbccdd' or '#aabbcc'."""

        representation = f"{self.red}:02x{self.green}:02x{self.blue}:02x"
        if self.alpha != 1.0:
            return f"#{int(self.alpha * 255)}:" + representation

        return "#" + representation

    def to_rgb_string(self) -> str:
        """Returns the RGB string representation of this colour in the format 'rgba(r, g, b, a)' or 'rgb(r, g, b)'."""

        if self.alpha != 1.0:
            return f"rgba({self.red}, {self.green}, {self.blue}, {self.alpha})"

        return f"rgb({self.red}, {self.green}, {self.blue})"

    def __str__(self) -> str:
        return self.to_rgb_string()

    def most_similar(self, palette: list[Self]) -> Self:
        """
        Returns the colour from the palette that this colour is most similar to.
        This method uses the Euclidean approximation.
        """

        current_best: tuple[Colour, float] = (self, float("inf"))
        for colour in palette:
            distance = math.sqrt(
                (self.red - colour.red) ** 2 + (self.green - colour.green) ** 2 + (self.blue - colour.blue) ** 2
            )
            if distance < current_best[1]:
                current_best = (colour, distance)

        return current_best[0]


Palette: TypeAlias = list[Colour]


def translate_colourscheme(original: JSON, palette: Palette, skip_keys: list[str]) -> JSON:
    """
    Translates a colour scheme in its JSON representation to an identical colour scheme matching the provided
    palette. This supports JSON with nested objects.

    All keys in the `skip_keys` list will not subject to conversion. This is for keys that do no contain colour scheme
    data.
    """

    translated = dict()
    for key, value in original.items():

        if key in skip_keys:
            translated[key] = value
            continue

        if type(value) is dict:
            translated[key] = translate_colourscheme(value, palette, skip_keys)
        elif type(value) is str:
            translated[key] = str(Colour.from_rgb_string(value).most_similar(palette))

    return translated


def main():

    # Set up parser
    parser = argparse.ArgumentParser(
        prog="Kicad Colourscheme Converter",
        description="Converts a KiCad colour scheme by translating its colours to match a user defined palette.",
        epilog="Author: Matteo Golin",
    )

    parser.add_argument("original", type=FileType(), help="The original KiCad colour scheme filepath.")
    parser.add_argument("out", type=FileType(mode="w"), help="The filepath to save the translated colour scheme.")
    parser.add_argument("palette", type=FileType(), help="The filepath of the JSON palette file.")
    parser.add_argument("name", type=str, help="The name of the new colour scheme.")

    args = parser.parse_args()

    # Load original colour scheme
    original = json.load(args.original)

    # Load palette
    loaded_palette: list[str] = json.load(args.palette)
    palette = [Colour.from_hex_string(c) for c in loaded_palette]

    # Translate
    translated = translate_colourscheme(original, palette, ["meta"])
    translated["meta"]["name"] = args.name
    json.dump(translated, args.out)


if __name__ == "__main__":
    main()
