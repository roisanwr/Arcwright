"""Arwright — PDF extraction, chunking, embedding pipeline.

Modules with heavy dependencies (embed, extract, refiner, enhancer, utils.llm)
are lazy-loaded on first use to avoid import errors.
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


def get_strategy():
    from . import strategy
    return strategy


def get_enhancer():
    from . import enhancer
    return enhancer


def get_boundary():
    from . import boundary
    return boundary


def get_pipeline():
    from . import pipeline
    return pipeline
