"""Arwright — PDF extraction, chunking, embedding pipeline.

Modules with heavy dependencies (embed, extract, refiner) are lazy-loaded
on first use to avoid import errors when dependencies are missing.
"""
from . import config
from . import cleanup
from . import chunk


def get_extract():
    from . import extract
    return extract


def get_embed():
    from . import embed
    return embed


def get_refiner():
    from . import refiner
    return refiner


def get_pipeline():
    from . import pipeline
    return pipeline
