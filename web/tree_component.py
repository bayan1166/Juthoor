"""
Clickable curriculum tree.

Streamlit removes <script> from st.markdown, so a leaf can not react to a tap by itself.
This wrapper renders the very same SVG (tree_view.tree_html) inside a tiny custom component
(components/jt_tree/index.html, plain HTML, no build step) that reports the tapped leaf's key.

If the component folder is missing the tree still shows (static), and app.py offers a
drop-down as a second way to pick a lesson.
"""
from __future__ import annotations

import os
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

import tree_view as tv

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "components", "jt_tree")

try:
    _cmp = components.declare_component("jt_tree", path=_DIR) if os.path.isdir(_DIR) else None
except Exception:                       # very old / unusual Streamlit builds
    _cmp = None


def available() -> bool:
    return _cmp is not None


def clickable_tree(state, selected: Optional[str] = None, key: str = "jt_tree") -> Optional[str]:
    """Draw the tree; return the lesson key of the last leaf tapped (None if nothing yet)."""
    html = tv.tree_html(state, selected)
    if _cmp is None:
        st.markdown(html, unsafe_allow_html=True)
        return None
    return _cmp(html=html, css=tv.TREE_CSS, key=key, default=None)
